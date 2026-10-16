from collections import Counter
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import MachineOperationalState, ProductionLine

router = APIRouter(tags=["Plant & Line Summaries"])

@router.get("/plants/{plant_id}/summary")
async def get_plant_summary(plant_id: str, session: AsyncSession = Depends(get_db)):
    """
    Returns aggregated plant overview: status distribution, lines needing attention,
    critical machines list, and stale machine counts.
    """
    query = select(MachineOperationalState).where(MachineOperationalState.plant_id == plant_id)
    res = await session.execute(query)
    machines: List[MachineOperationalState] = list(res.scalars().all())

    if not machines:
        raise HTTPException(status_code=404, detail=f"No machines found for plant '{plant_id}'.")

    status_counts = Counter(m.derived_status for m in machines)
    critical_machines = [m.machine_id for m in machines if m.attention_level == "CRITICAL"]
    attention_machines = [m for m in machines if m.needs_attention]
    stale_count = sum(1 for m in machines if m.is_stale)

    # Group by line
    line_attention = Counter(m.line_id for m in attention_machines)
    lines_summary = [
        {"line_id": line_id, "machines_needing_attention": count}
        for line_id, count in line_attention.most_common()
    ]

    return {
        "plant_id": plant_id,
        "total_machines": len(machines),
        "machines_by_status": dict(status_counts),
        "machines_requiring_attention": len(attention_machines),
        "critical_machines": critical_machines,
        "lines_requiring_attention_ranking": lines_summary,
        "stale_machines_count": stale_count,
    }

@router.get("/lines/{line_id}/summary")
async def get_line_summary(line_id: str, session: AsyncSession = Depends(get_db)):
    """
    Returns line overview: status counts, critical machines, operating window.
    """
    line_record = await session.get(ProductionLine, line_id)
    query = select(MachineOperationalState).where(MachineOperationalState.line_id == line_id)
    res = await session.execute(query)
    machines: List[MachineOperationalState] = list(res.scalars().all())

    if not machines and not line_record:
        raise HTTPException(status_code=404, detail=f"Production line '{line_id}' not found.")

    status_counts = Counter(m.derived_status for m in machines)
    critical_machines = [m.machine_id for m in machines if m.attention_level == "CRITICAL"]
    attention_machines = [m for m in machines if m.needs_attention]

    return {
        "line_id": line_id,
        "plant_id": line_record.plant_id if line_record else (machines[0].plant_id if machines else "UNKNOWN"),
        "line_name": line_record.line_name if line_record else "Unknown Line",
        "operating_window": line_record.operating_window if line_record else "Unknown",
        "total_machines": len(machines),
        "machines_by_status": dict(status_counts),
        "machines_requiring_attention": len(attention_machines),
        "critical_machines": critical_machines,
    }
