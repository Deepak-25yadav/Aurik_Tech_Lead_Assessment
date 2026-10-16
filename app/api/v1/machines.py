from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import MachineOperationalState, Asset
from app.schemas.canonical import MachineOperationalViewResponse

router = APIRouter(prefix="/machines", tags=["Machine Operational View"])

@router.get("", response_model=List[MachineOperationalViewResponse])
async def list_all_machines(
    plant_id: Optional[str] = Query(None, description="Filter by plant"),
    line_id: Optional[str] = Query(None, description="Filter by production line"),
    session: AsyncSession = Depends(get_db),
):
    query = select(MachineOperationalState)
    if plant_id:
        query = query.where(MachineOperationalState.plant_id == plant_id)
    if line_id:
        query = query.where(MachineOperationalState.line_id == line_id)

    result = await session.execute(query)
    return list(result.scalars().all())

@router.get("/attention", response_model=List[MachineOperationalViewResponse])
async def get_machines_requiring_attention(
    plant_id: Optional[str] = Query(None, description="Filter by plant"),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns prioritized list of machines needing maintenance, inspection, or attention.
    """
    query = select(MachineOperationalState).where(MachineOperationalState.needs_attention.is_(True))
    if plant_id:
        query = query.where(MachineOperationalState.plant_id == plant_id)

    result = await session.execute(query)
    states = list(result.scalars().all())

    # Sort: CRITICAL > HIGH > MEDIUM
    severity_rank = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0, "NOMINAL": -1}
    states.sort(key=lambda s: severity_rank.get(s.attention_level, 0), reverse=True)
    return states

@router.get("/{machine_id}/operational-view", response_model=MachineOperationalViewResponse)
async def get_machine_operational_view(
    machine_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Returns current derived operational status, whether machine needs attention,
    attention level, explainable reason codes, latest signals, and source refs.
    """
    state = await session.get(MachineOperationalState, machine_id)
    if not state:
        # Check if asset exists in catalog
        asset = await session.get(Asset, machine_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found in catalog.")
        raise HTTPException(status_code=404, detail=f"No operational state derived for machine '{machine_id}'.")

    return state
