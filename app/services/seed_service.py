import csv
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.catalog_service import seed_reference_catalog
from app.services.ingestion_service import process_ingestion_payload

async def load_all_seed_data(session: AsyncSession, data_dir: Path) -> Dict[str, Any]:
    """
    Seeds catalog reference data, then ingests all vendor seed CSVs:
    PulseForge, ThermexWatch, and MaintaFlow.
    """
    # 1. Seed base catalog
    await seed_reference_catalog(session, data_dir)

    results = {}
    seed_dir = data_dir / "seed_data"

    # 2. PulseForge Seed
    pf_file = seed_dir / "pulseforge_events.csv"
    if pf_file.exists():
        events = []
        with open(pf_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append({
                    "event_id": row["event_id"],
                    "machine_id": row["machine_id"],
                    "line_id": row["line_id"],
                    "event_time": row["event_time"],
                    "event_type": row["event_type"],
                    "severity": row["severity"],
                    "vibration_mm_s": float(row["vibration_mm_s"]) if row.get("vibration_mm_s") else None,
                    "temperature_c": float(row["temperature_c"]) if row.get("temperature_c") else None,
                    "machine_state": row.get("machine_state"),
                    "sensor_health": float(row["sensor_health"]) if row.get("sensor_health") else None,
                    "vendor_confidence": float(row["vendor_confidence"]) if row.get("vendor_confidence") else None,
                })
        payload = {"vendor": "PulseForge", "events": events}
        job = await process_ingestion_payload(session, "PulseForge", payload)
        results["pulseforge"] = {
            "job_id": job.job_id,
            "status": job.status,
            "processed": job.records_processed,
            "quarantined": job.records_quarantined,
            "duplicate": job.records_duplicate,
        }

    # 3. ThermexWatch Seed
    tw_file = seed_dir / "thermexwatch_readings.csv"
    if tw_file.exists():
        readings = []
        with open(tw_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                readings.append({
                    "readingId": row["reading_id"],
                    "assetCode": row["asset_code"],
                    "productionLine": row["production_line"],
                    "timestampMs": int(row["timestamp_ms"]) if row.get("timestamp_ms") else None,
                    "alertCode": row.get("alert_code"),
                    "level": int(row["level"]) if row.get("level") else 1,
                    "vibration_g": float(row["vibration_g"]) if row.get("vibration_g") else None,
                    "temperature_f": float(row["temperature_f"]) if row.get("temperature_f") else None,
                    "power_kw": float(row["power_kw"]) if row.get("power_kw") else None,
                    "is_active": row.get("is_active", "").lower() == "true",
                    "signal_quality": row.get("signal_quality"),
                })
        payload = {"source": "ThermexWatch", "readings": readings}
        job = await process_ingestion_payload(session, "ThermexWatch", payload)
        results["thermexwatch"] = {
            "job_id": job.job_id,
            "status": job.status,
            "processed": job.records_processed,
            "quarantined": job.records_quarantined,
        }

    # 4. MaintaFlow Seed
    mf_file = seed_dir / "maintaflow_records.csv"
    if mf_file.exists():
        records = []
        with open(mf_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "record_id": row["record_id"],
                    "machine_ref": row["machine_ref"],
                    "line_ref": row["line_ref"],
                    "recorded_at": row["recorded_at"],
                    "record_type": row.get("record_type"),
                    "inspection_result": row.get("inspection_result") or None,
                    "maintenance_status": row.get("maintenance_status") or None,
                    "days_since_last_service": float(row["days_since_last_service"]) if row.get("days_since_last_service") else None,
                    "technician_note": row.get("technician_note") or None,
                    "manual_confidence": row.get("manual_confidence"),
                })
        payload = {"provider_name": "MaintaFlow", "records": records}
        job = await process_ingestion_payload(session, "MaintaFlow", payload)
        results["maintaflow"] = {
            "job_id": job.job_id,
            "status": job.status,
            "processed": job.records_processed,
            "quarantined": job.records_quarantined,
        }

    return results
