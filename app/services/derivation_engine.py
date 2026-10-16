from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Asset,
    CanonicalEvent,
    MachineOperationalState,
    MaintenanceWorkOrder,
)
from app.core.constants import (
    DerivedStatus,
    AttentionLevel,
    MachinePhysicalState,
)
from app.core.config import settings

SEVERITY_ORDER = {
    AttentionLevel.NOMINAL.value: 0,
    AttentionLevel.LOW.value: 1,
    AttentionLevel.MEDIUM.value: 2,
    AttentionLevel.HIGH.value: 3,
    AttentionLevel.CRITICAL.value: 4,
}

def escalate_attention(current: str, candidate: str) -> str:
    current_val = SEVERITY_ORDER.get(current, 0)
    candidate_val = SEVERITY_ORDER.get(candidate, 0)
    return candidate if candidate_val > current_val else current

async def recompute_machine_operational_state(session: AsyncSession, machine_id: str) -> MachineOperationalState:
    """
    Deterministically computes the machine's operational attention view by synthesizing:
    1. Machine metadata & rated thresholds (Asset catalog)
    2. Open maintenance work orders
    3. Chronologically ordered canonical telemetry and inspection events
    """
    asset = await session.get(Asset, machine_id)
    rated_temp = asset.rated_max_temp_c if asset else settings.DEFAULT_RATED_MAX_TEMP_C
    rated_vib = asset.rated_max_vibration_mm_s if asset else settings.DEFAULT_RATED_MAX_VIB_MM_S
    baseline_power = asset.baseline_power_kw if asset else settings.DEFAULT_BASELINE_POWER_KW
    criticality = asset.criticality if asset else "medium"
    plant_id = asset.plant_id if asset else "UNKNOWN_PLANT"
    line_id = asset.line_id if asset else "UNKNOWN_LINE"

    # Fetch all events chronologically (out-of-order resolved here)
    events_query = (
        select(CanonicalEvent)
        .where(CanonicalEvent.machine_id == machine_id)
        .order_by(CanonicalEvent.event_time.asc())
    )
    res_events = await session.execute(events_query)
    events: List[CanonicalEvent] = list(res_events.scalars().all())

    # Fetch open work orders
    wo_query = (
        select(MaintenanceWorkOrder)
        .where(MaintenanceWorkOrder.machine_id == machine_id, MaintenanceWorkOrder.status == "open")
    )
    res_wos = await session.execute(wo_query)
    open_wos: List[MaintenanceWorkOrder] = list(res_wos.scalars().all())

    reason_codes: List[str] = []
    attention_level = AttentionLevel.NOMINAL.value
    derived_status = DerivedStatus.NORMAL.value
    
    latest_event: Optional[CanonicalEvent] = events[-1] if events else None
    latest_event_time = latest_event.event_time if latest_event else None

    # Track latest known metric values across events
    latest_temp: Optional[float] = None
    latest_vib: Optional[float] = None
    latest_power: Optional[float] = None
    latest_sh: Optional[float] = None
    latest_state: str = MachinePhysicalState.RUNNING.value
    latest_insp: Optional[str] = None
    latest_note: Optional[str] = None

    for ev in events:
        if ev.temperature_c is not None:
            latest_temp = ev.temperature_c
        if ev.vibration_mm_s is not None:
            latest_vib = ev.vibration_mm_s
        if ev.power_kw is not None:
            latest_power = ev.power_kw
        if ev.sensor_health is not None:
            latest_sh = ev.sensor_health
        if ev.machine_state:
            latest_state = ev.machine_state
        if ev.inspection_result:
            latest_insp = ev.inspection_result
        if ev.technician_note:
            latest_note = ev.technician_note

    # 1. Evaluate Open Work Orders
    if open_wos:
        attention_level = escalate_attention(attention_level, AttentionLevel.MEDIUM.value)
        derived_status = DerivedStatus.MAINTENANCE_REQUIRED.value
        for wo in open_wos:
            reason_codes.append(f"OPEN_WORK_ORDER ({wo.work_order_id}: {wo.maintenance_type})")

    # 2. Evaluate Inspection Defect History
    if latest_insp == "major_defect_found":
        attention_level = escalate_attention(attention_level, AttentionLevel.CRITICAL.value)
        derived_status = DerivedStatus.MAINTENANCE_REQUIRED.value
        note_str = f" - {latest_note}" if latest_note else ""
        reason_codes.append(f"MAJOR_INSPECTION_DEFECT_ACTIVE{note_str}")
    elif latest_insp == "minor_defect_found":
        attention_level = escalate_attention(attention_level, AttentionLevel.HIGH.value)
        if derived_status != DerivedStatus.MAINTENANCE_REQUIRED.value:
            derived_status = DerivedStatus.WARNING.value
        note_str = f" - {latest_note}" if latest_note else ""
        reason_codes.append(f"MINOR_INSPECTION_DEFECT_ACTIVE{note_str}")

    # 3. Evaluate Sensor Readings
    if latest_temp is not None:
        if latest_temp > rated_temp:
            if latest_temp >= rated_temp + 5.0 or criticality == "high":
                attention_level = escalate_attention(attention_level, AttentionLevel.CRITICAL.value)
                derived_status = DerivedStatus.CRITICAL.value
                reason_codes.append(f"OVER_TEMPERATURE_CRITICAL ({latest_temp:.1f}°C > rated max {rated_temp:.1f}°C)")
            else:
                attention_level = escalate_attention(attention_level, AttentionLevel.HIGH.value)
                if derived_status not in [DerivedStatus.CRITICAL.value, DerivedStatus.MAINTENANCE_REQUIRED.value]:
                    derived_status = DerivedStatus.WARNING.value
                reason_codes.append(f"OVER_TEMPERATURE_WARNING ({latest_temp:.1f}°C > rated max {rated_temp:.1f}°C)")

    if latest_vib is not None:
        if latest_vib > rated_vib:
            target_att = AttentionLevel.CRITICAL.value if criticality == "high" else AttentionLevel.HIGH.value
            attention_level = escalate_attention(attention_level, target_att)
            if derived_status != DerivedStatus.CRITICAL.value:
                derived_status = DerivedStatus.WARNING.value if target_att != AttentionLevel.CRITICAL.value else DerivedStatus.CRITICAL.value
            reason_codes.append(f"EXCESSIVE_VIBRATION ({latest_vib:.1f} mm/s > rated max {rated_vib:.1f} mm/s)")

    if latest_sh is not None and latest_sh < 0.60:
        attention_level = escalate_attention(attention_level, AttentionLevel.MEDIUM.value)
        if derived_status == DerivedStatus.NORMAL.value:
            derived_status = DerivedStatus.DEGRADED.value
        reason_codes.append(f"SENSOR_HEALTH_DEGRADED ({latest_sh:.2f} < 0.60 threshold)")

    if latest_power is not None:
        if latest_power > baseline_power * 1.35 or latest_power < baseline_power * 0.40:
            attention_level = escalate_attention(attention_level, AttentionLevel.MEDIUM.value)
            reason_codes.append(f"POWER_ANOMALY ({latest_power:.1f} kW vs baseline {baseline_power:.1f} kW)")

    # 4. Recovery Signal Handling
    if latest_event and latest_event.event_type == "RECOVERY_SIGNAL":
        # If latest sensor values are below rated limits, de-escalate unless major defect is open
        if (latest_temp is None or latest_temp <= rated_temp) and (latest_vib is None or latest_vib <= rated_vib):
            if latest_insp != "major_defect_found" and not open_wos:
                attention_level = AttentionLevel.NOMINAL.value
                derived_status = DerivedStatus.NORMAL.value
                reason_codes = ["RECOVERY_SIGNAL_VERIFIED (readings nominal)"]
            else:
                reason_codes.append("RECOVERY_SIGNAL_REPORTED (still subject to open defects)")

    # If no reasons flagged
    if not reason_codes:
        reason_codes.append("NOMINAL_OPERATION")
        attention_level = AttentionLevel.NOMINAL.value
        derived_status = DerivedStatus.NORMAL.value

    needs_attention = SEVERITY_ORDER.get(attention_level, 0) >= SEVERITY_ORDER[AttentionLevel.MEDIUM.value]

    # Source event references (latest 5 event IDs)
    source_refs = [e.source_event_id for e in reversed(events[-5:])]

    # Check staleness
    is_stale = False
    now = datetime.now(timezone.utc)
    if latest_event_time:
        if latest_event_time.tzinfo is None:
            latest_event_time = latest_event_time.replace(tzinfo=timezone.utc)
        age_seconds = (now - latest_event_time).total_seconds()
        # Stale if older than threshold
        if age_seconds > settings.STALENESS_THRESHOLD_SECONDS:
            is_stale = True
            reason_codes.append("STALE_TELEMETRY")

    # Save to state table
    state = await session.get(MachineOperationalState, machine_id)
    if not state:
        state = MachineOperationalState(machine_id=machine_id)
        session.add(state)

    state.plant_id = plant_id
    state.line_id = line_id
    state.derived_status = derived_status
    state.needs_attention = needs_attention
    state.attention_level = attention_level
    state.reason_codes = reason_codes
    state.latest_relevant_event_time = latest_event_time
    state.latest_temperature_c = latest_temp
    state.latest_vibration_mm_s = latest_vib
    state.latest_power_kw = latest_power
    state.latest_sensor_health = latest_sh
    state.latest_machine_state = latest_state
    state.latest_inspection_result = latest_insp
    state.latest_technician_note = latest_note
    state.source_event_refs = source_refs
    state.processing_status = "PROCESSED"
    state.is_stale = is_stale
    state.last_processed_at = now

    await session.commit()
    await session.refresh(state)
    return state
