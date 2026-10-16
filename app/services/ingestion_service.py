import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    IngestionJob,
    RawIngestionLog,
    CanonicalEvent,
    DeadLetterRecord,
    Asset,
)
from app.core.constants import IngestionJobStatus
from app.services.normalization_service import (
    normalize_pulseforge_event,
    normalize_thermexwatch_reading,
    normalize_maintaflow_record,
)
from app.services.derivation_engine import recompute_machine_operational_state

async def load_asset_catalog_map(session: AsyncSession) -> Dict[str, Asset]:
    result = await session.execute(select(Asset))
    assets = result.scalars().all()
    return {a.machine_id: a for a in assets}

async def process_ingestion_payload(
    session: AsyncSession,
    vendor_type: str,
    raw_payload: Dict[str, Any],
    job_id: Optional[str] = None,
) -> IngestionJob:
    """
    Ingests and normalizes vendor payloads, routes malformed records to DLQ,
    deduplicates events, and triggers state derivation for affected machines.
    """
    if not job_id:
        job_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    
    # Save raw audit log
    raw_log = RawIngestionLog(
        job_id=job_id,
        vendor=vendor_type,
        received_at=now,
        raw_payload=json.dumps(raw_payload, default=str),
        record_count=0,
    )
    session.add(raw_log)

    job = IngestionJob(
        job_id=job_id,
        vendor=vendor_type,
        status=IngestionJobStatus.PROCESSING.value,
        records_total=0,
        records_processed=0,
        records_quarantined=0,
        records_duplicate=0,
        created_at=now,
    )
    session.add(job)
    await session.commit()

    asset_map = await load_asset_catalog_map(session)
    affected_machines: Set[str] = set()

    # Normalize records depending on vendor or multi-vendor envelope
    records_to_process: List[tuple] = [] # (vendor_name, item, default_plant_id)

    if vendor_type.lower() == "pulseforge":
        plant_id = raw_payload.get("plant_id")
        for ev in raw_payload.get("events", []):
            records_to_process.append(("PulseForge", ev, plant_id))

    elif vendor_type.lower() == "thermexwatch":
        site_code = raw_payload.get("site_code")
        for rd in raw_payload.get("readings", []):
            records_to_process.append(("ThermexWatch", rd, site_code))

    elif vendor_type.lower() == "maintaflow":
        factory_id = raw_payload.get("factory_id")
        for rc in raw_payload.get("records", []):
            records_to_process.append(("MaintaFlow", rc, factory_id))

    elif vendor_type.lower() == "batch" or "pulseforge" in raw_payload or "thermexwatch" in raw_payload or "maintaflow" in raw_payload:
        # Multi-vendor envelope
        if "pulseforge" in raw_payload:
            pf = raw_payload["pulseforge"]
            for ev in pf.get("events", []):
                records_to_process.append(("PulseForge", ev, pf.get("plant_id")))
        if "thermexwatch" in raw_payload:
            tw = raw_payload["thermexwatch"]
            for rd in tw.get("readings", []):
                records_to_process.append(("ThermexWatch", rd, tw.get("site_code")))
        if "maintaflow" in raw_payload:
            mf = raw_payload["maintaflow"]
            for rc in mf.get("records", []):
                records_to_process.append(("MaintaFlow", rc, mf.get("factory_id")))

    job.records_total = len(records_to_process)
    raw_log.record_count = len(records_to_process)

    # Process each record individually to isolate errors
    for v_name, item, default_site in records_to_process:
        try:
            if v_name == "PulseForge":
                canonical = normalize_pulseforge_event(item, default_site, asset_map, job_id)
            elif v_name == "ThermexWatch":
                canonical = normalize_thermexwatch_reading(item, default_site, asset_map, job_id)
            elif v_name == "MaintaFlow":
                canonical = normalize_maintaflow_record(item, default_site, asset_map, job_id)
            else:
                raise ValueError(f"Unknown vendor: {v_name}")

            # Deduplication check: exact dedup_hash in database
            dedup_check = await session.execute(
                select(CanonicalEvent).where(CanonicalEvent.dedup_hash == canonical.dedup_hash)
            )
            existing_event = dedup_check.scalar_one_or_none()

            # Also check semantic duplicate (same machine, exact timestamp, same temp and vib)
            if not existing_event and canonical.temperature_c is not None:
                sem_check = await session.execute(
                    select(CanonicalEvent).where(
                        CanonicalEvent.machine_id == canonical.machine_id,
                        CanonicalEvent.event_time == canonical.event_time,
                        CanonicalEvent.temperature_c == canonical.temperature_c,
                    )
                )
                existing_event = sem_check.scalar_one_or_none()

            if existing_event:
                job.records_duplicate += 1
                continue

            session.add(canonical)
            job.records_processed += 1
            affected_machines.add(canonical.machine_id)

        except Exception as e:
            # Route to quarantine Dead Letter Queue
            dlq = DeadLetterRecord(
                job_id=job_id,
                vendor=v_name,
                raw_record=json.dumps(item, default=str),
                error_code="RECORD_NORMALIZATION_FAILED",
                error_reason=str(e),
                quarantined_at=datetime.now(timezone.utc),
            )
            session.add(dlq)
            job.records_quarantined += 1

    await session.commit()

    # Recompute state for all affected machines
    for m_id in affected_machines:
        await recompute_machine_operational_state(session, m_id)

    # Update final job status
    if job.records_quarantined == 0 and job.records_total > 0:
        job.status = IngestionJobStatus.COMPLETED.value
    elif job.records_processed > 0:
        job.status = IngestionJobStatus.PARTIAL_SUCCESS.value
        job.error_summary = f"{job.records_quarantined} records quarantined to DLQ."
    elif job.records_total == 0:
        job.status = IngestionJobStatus.COMPLETED.value
    else:
        job.status = IngestionJobStatus.FAILED.value
        job.error_summary = "All records failed normalization and were quarantined."

    job.completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(job)
    return job
