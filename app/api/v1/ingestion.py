import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.async_pipeline import run_async_ingestion_job
from app.services.ingestion_service import process_ingestion_payload

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("/pulseforge", status_code=status.HTTP_202_ACCEPTED)
async def ingest_pulseforge(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    is_async: bool = Query(True, alias="async", description="Set to false to process synchronously"),
    session: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    if is_async:
        background_tasks.add_task(run_async_ingestion_job, "PulseForge", payload, job_id)
        return {
            "status": "ACCEPTED",
            "job_id": job_id,
            "vendor": "PulseForge",
            "message": "Payload queued for background normalization and state recomputation.",
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }
    else:
        job = await process_ingestion_payload(session, "PulseForge", payload, job_id)
        return {
            "status": job.status,
            "job_id": job.job_id,
            "vendor": "PulseForge",
            "records_total": job.records_total,
            "records_processed": job.records_processed,
            "records_quarantined": job.records_quarantined,
            "records_duplicate": job.records_duplicate,
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }

@router.post("/thermexwatch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_thermexwatch(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    is_async: bool = Query(True, alias="async", description="Set to false to process synchronously"),
    session: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    if is_async:
        background_tasks.add_task(run_async_ingestion_job, "ThermexWatch", payload, job_id)
        return {
            "status": "ACCEPTED",
            "job_id": job_id,
            "vendor": "ThermexWatch",
            "message": "Payload queued for background normalization and state recomputation.",
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }
    else:
        job = await process_ingestion_payload(session, "ThermexWatch", payload, job_id)
        return {
            "status": job.status,
            "job_id": job.job_id,
            "vendor": "ThermexWatch",
            "records_total": job.records_total,
            "records_processed": job.records_processed,
            "records_quarantined": job.records_quarantined,
            "records_duplicate": job.records_duplicate,
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }

@router.post("/maintaflow", status_code=status.HTTP_202_ACCEPTED)
async def ingest_maintaflow(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    is_async: bool = Query(True, alias="async", description="Set to false to process synchronously"),
    session: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    if is_async:
        background_tasks.add_task(run_async_ingestion_job, "MaintaFlow", payload, job_id)
        return {
            "status": "ACCEPTED",
            "job_id": job_id,
            "vendor": "MaintaFlow",
            "message": "Payload queued for background normalization and state recomputation.",
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }
    else:
        job = await process_ingestion_payload(session, "MaintaFlow", payload, job_id)
        return {
            "status": job.status,
            "job_id": job.job_id,
            "vendor": "MaintaFlow",
            "records_total": job.records_total,
            "records_processed": job.records_processed,
            "records_quarantined": job.records_quarantined,
            "records_duplicate": job.records_duplicate,
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }

@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_batch(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    is_async: bool = Query(True, alias="async", description="Set to false to process synchronously"),
    session: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    if is_async:
        background_tasks.add_task(run_async_ingestion_job, "batch", payload, job_id)
        return {
            "status": "ACCEPTED",
            "job_id": job_id,
            "vendor": "multi_vendor_batch",
            "message": "Batch envelope queued for background normalization and state recomputation.",
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }
    else:
        job = await process_ingestion_payload(session, "batch", payload, job_id)
        return {
            "status": job.status,
            "job_id": job.job_id,
            "vendor": "multi_vendor_batch",
            "records_total": job.records_total,
            "records_processed": job.records_processed,
            "records_quarantined": job.records_quarantined,
            "records_duplicate": job.records_duplicate,
            "status_url": f"/api/v1/ingestion/status/{job_id}",
        }
