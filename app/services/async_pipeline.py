import logging
from typing import Dict, Any
from app.db.session import async_session_maker
from app.services.ingestion_service import process_ingestion_payload

logger = logging.getLogger(__name__)

async def run_async_ingestion_job(vendor_type: str, raw_payload: Dict[str, Any], job_id: str):
    """
    Background worker task to execute ingestion and normalization asynchronously.
    """
    async with async_session_maker() as session:
        try:
            await process_ingestion_payload(
                session=session,
                vendor_type=vendor_type,
                raw_payload=raw_payload,
                job_id=job_id,
            )
            logger.info(f"Async ingestion job {job_id} for vendor {vendor_type} completed.")
        except Exception as e:
            logger.error(f"Error in async ingestion job {job_id}: {str(e)}", exc_info=True)
