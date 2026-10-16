import csv
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ProductionLine, Asset, MaintenanceWorkOrder, MachineOperationalState
from app.core.constants import DerivedStatus, AttentionLevel, MachinePhysicalState

async def seed_reference_catalog(session: AsyncSession, data_dir: Path):
    """
    Seeds production lines, asset references, and maintenance work orders into database.
    Idempotent: updates existing or inserts if not present.
    """
    line_file = data_dir / "line_reference.csv"
    if line_file.exists():
        with open(line_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                line_id = row["line_id"].strip()
                existing = await session.get(ProductionLine, line_id)
                if not existing:
                    line = ProductionLine(
                        line_id=line_id,
                        plant_id=row["plant_id"].strip(),
                        line_name=row["line_name"].strip(),
                        operating_window=row["operating_window"].strip(),
                    )
                    session.add(line)

    asset_file = data_dir / "asset_reference.csv"
    if asset_file.exists():
        with open(asset_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                machine_id = row["machine_id"].strip()
                existing = await session.get(Asset, machine_id)
                if not existing:
                    asset = Asset(
                        machine_id=machine_id,
                        plant_id=row["plant_id"].strip(),
                        line_id=row["line_id"].strip(),
                        machine_type=row["machine_type"].strip(),
                        criticality=row["criticality"].strip().lower(),
                        installed_date=row.get("installed_date", "").strip(),
                        rated_max_temp_c=float(row.get("rated_max_temp_c", 85.0)),
                        rated_max_vibration_mm_s=float(row.get("rated_max_vibration_mm_s", 8.5)),
                        baseline_power_kw=float(row.get("baseline_power_kw", 25.0)),
                        asset_status=row.get("asset_status", "active").strip().lower(),
                    )
                    session.add(asset)

                # Initialize initial operational state if not exists
                state = await session.get(MachineOperationalState, machine_id)
                if not state:
                    initial_state = MachineOperationalState(
                        machine_id=machine_id,
                        plant_id=row["plant_id"].strip(),
                        line_id=row["line_id"].strip(),
                        derived_status=DerivedStatus.NORMAL.value if row.get("asset_status") == "active" else DerivedStatus.MAINTENANCE_REQUIRED.value,
                        needs_attention=False if row.get("asset_status") == "active" else True,
                        attention_level=AttentionLevel.NOMINAL.value if row.get("asset_status") == "active" else AttentionLevel.MEDIUM.value,
                        reason_codes=["INITIAL_CATALOG_STATE"],
                        latest_machine_state=MachinePhysicalState.IDLE.value,
                        source_event_refs=[],
                        processing_status="INITIALIZED",
                    )
                    session.add(initial_state)

    # Seed work orders if file exists
    wo_file = data_dir / "seed_data" / "maintenance_work_orders.csv"
    if wo_file.exists():
        with open(wo_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wo_id = row["work_order_id"].strip()
                existing = await session.get(MaintenanceWorkOrder, wo_id)
                if not existing:
                    wo = MaintenanceWorkOrder(
                        work_order_id=wo_id,
                        plant_id=row["plant_id"].strip(),
                        machine_id=row["machine_id"].strip(),
                        line_id=row["line_id"].strip(),
                        opened_at=row["opened_at"].strip(),
                        closed_at=row.get("closed_at", "").strip() or None,
                        maintenance_type=row["maintenance_type"].strip(),
                        trigger_source=row["trigger_source"].strip(),
                        status=row["status"].strip().lower(),
                        downtime_minutes=int(row.get("downtime_minutes", 0) or 0),
                        post_maintenance_check=row.get("post_maintenance_check", "").strip() or None,
                        notes=row.get("notes", "").strip() or None,
                    )
                    session.add(wo)

    await session.commit()

async def get_all_assets(session: AsyncSession) -> List[Asset]:
    result = await session.execute(select(Asset))
    return list(result.scalars().all())

async def get_asset(session: AsyncSession, machine_id: str) -> Optional[Asset]:
    return await session.get(Asset, machine_id)

async def get_all_lines(session: AsyncSession) -> List[ProductionLine]:
    result = await session.execute(select(ProductionLine))
    return list(result.scalars().all())

async def get_line(session: AsyncSession, line_id: str) -> Optional[ProductionLine]:
    return await session.get(ProductionLine, line_id)

async def get_open_work_orders(session: AsyncSession, machine_id: str) -> List[MaintenanceWorkOrder]:
    query = select(MaintenanceWorkOrder).where(
        MaintenanceWorkOrder.machine_id == machine_id,
        MaintenanceWorkOrder.status == "open",
    )
    result = await session.execute(query)
    return list(result.scalars().all())
