from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import IngestionJob, DeadLetterRecord

router = APIRouter(prefix="/ingestion", tags=["Processing Status"])

@router.get("/status/{job_id}")
async def get_job_status(job_id: str, session: AsyncSession = Depends(get_db)):
    job = await session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job '{job_id}' not found.")

    duration_ms = None
    if job.completed_at and job.created_at:
        duration_ms = int((job.completed_at - job.created_at).total_seconds() * 1000)

    return {
        "job_id": job.job_id,
        "vendor": job.vendor,
        "status": job.status,
        "records_total": job.records_total,
        "records_processed": job.records_processed,
        "records_quarantined": job.records_quarantined,
        "records_duplicate": job.records_duplicate,
        "error_summary": job.error_summary,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "duration_ms": duration_ms,
    }

@router.get("/dead-letter-queue")
async def get_dead_letter_queue(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    query = select(DeadLetterRecord)
    if job_id:
        query = query.where(DeadLetterRecord.job_id == job_id)
    query = query.order_by(DeadLetterRecord.quarantined_at.desc()).limit(limit)

    result = await session.execute(query)
    records = result.scalars().all()

    return {
        "total_quarantined": len(records),
        "records": [
            {
                "id": r.id,
                "job_id": r.job_id,
                "vendor": r.vendor,
                "error_code": r.error_code,
                "error_reason": r.error_reason,
                "raw_record": r.raw_record,
                "quarantined_at": r.quarantined_at,
            }
            for r in records
        ],
    }
