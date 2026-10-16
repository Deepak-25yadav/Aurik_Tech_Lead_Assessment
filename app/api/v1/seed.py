from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.config import settings
from app.services.seed_service import load_all_seed_data

router = APIRouter(prefix="/seed", tags=["Seed Data"])

@router.post("/load-all")
async def seed_all_data(session: AsyncSession = Depends(get_db)):
    """
    Ingests all local seed datasets (catalog, pulseforge, thermexwatch, maintaflow)
    and recomputes derived operational views for immediate live testing.
    """
    results = await load_all_seed_data(session, settings.DATA_DIR)
    return {
        "status": "SUCCESS",
        "message": "All seed reference catalogs and vendor batches ingested successfully.",
        "results": results,
    }
