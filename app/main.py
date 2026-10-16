from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import init_db, async_session_maker
from app.services.catalog_service import seed_reference_catalog
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables on startup
    await init_db()
    
    # Automatically seed reference catalog if empty
    async with async_session_maker() as session:
        await seed_reference_catalog(session, settings.DATA_DIR)
        
    yield
    # Cleanup on shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Industrial Equipment Monitoring Backend Service (Aurik Tech Lead Take-Home)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Industrial Equipment Monitoring Service is active.",
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_STR,
    }
