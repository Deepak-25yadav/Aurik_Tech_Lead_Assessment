import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.db.models import Asset, ProductionLine, MaintenanceWorkOrder, MachineOperationalState
from app.services.catalog_service import seed_reference_catalog, get_all_assets, get_asset, get_open_work_orders

@pytest.mark.asyncio
async def test_seed_reference_catalog():
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    data_dir = Path(__file__).resolve().parent.parent

    async with session_factory() as session:
        await seed_reference_catalog(session, data_dir)

    async with session_factory() as session:
        assets = await get_all_assets(session)
        assert len(assets) == 8, f"Expected 8 machines, got {len(assets)}"
        
        # Verify machine details
        eq1 = await get_asset(session, "EQ-001")
        assert eq1 is not None
        assert eq1.plant_id == "PLANT_01"
        assert eq1.line_id == "LINE-A"
        assert eq1.machine_type == "Press"
        assert eq1.criticality == "high"
        assert eq1.rated_max_temp_c == 85.0
        assert eq1.rated_max_vibration_mm_s == 9.0

        # Verify operational state created
        state1 = await session.get(MachineOperationalState, "EQ-001")
        assert state1 is not None
        assert state1.derived_status == "NORMAL"
        assert state1.needs_attention is False

        # Verify open work orders
        open_wos = await get_open_work_orders(session, "EQ-002")
        assert len(open_wos) >= 1
        assert open_wos[0].work_order_id == "WO-1001"
        assert open_wos[0].status == "open"
