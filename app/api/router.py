from fastapi import APIRouter
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.status import router as status_router
from app.api.v1.machines import router as machines_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.seed import router as seed_router

api_router = APIRouter()
api_router.include_router(ingestion_router)
api_router.include_router(status_router)
api_router.include_router(machines_router)
api_router.include_router(summaries_router)
api_router.include_router(seed_router)
