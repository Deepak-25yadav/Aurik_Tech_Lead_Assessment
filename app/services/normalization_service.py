import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dateutil import parser as date_parser
from app.db.models import CanonicalEvent, Asset
from app.core.constants import MachinePhysicalState, AttentionLevel

def parse_utc_timestamp(ts_value: Any) -> datetime:
    """
    Parses various timestamp formats (ISO strings, epoch ms, slash dates, dash dates) into timezone-aware UTC datetime.
    Raises ValueError on invalid formats.
    """
    if ts_value is None or ts_value == "":
        raise ValueError("Timestamp is missing or empty")

    # If epoch milliseconds or seconds (int or numeric float)
    if isinstance(ts_value, (int, float)):
        # Epoch ms typically > 1e11
        if ts_value > 1e11:
            return datetime.fromtimestamp(ts_value / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(ts_value, tz=timezone.utc)

    if isinstance(ts_value, str):
        cleaned = ts_value.strip()
        if cleaned.isdigit():
            val = int(cleaned)
            if val > 1e11:
                return datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
            return datetime.fromtimestamp(val, tz=timezone.utc)

        try:
            dt = date_parser.parse(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception as e:
            raise ValueError(f"Invalid timestamp format: '{ts_value}' ({str(e)})")

    raise ValueError(f"Unsupported timestamp type: {type(ts_value)}")

def normalize_line_id(raw_line: Optional[str], asset: Optional[Asset] = None) -> str:
    """
    Normalizes production line references: 'A' -> 'LINE-A', 'LINE-A' -> 'LINE-A',
    or falls back to asset catalog reference.
    """
    if raw_line:
        clean = str(raw_line).strip().upper()
        if clean in ["A", "B", "C", "D", "E"]:
            return f"LINE-{clean}"
        if clean.startswith("LINE-"):
            return clean

    if asset and asset.line_id:
        return asset.line_id

    return str(raw_line).strip() if raw_line else "UNKNOWN_LINE"

def calculate_dedup_hashes(vendor: str, event_id: str, machine_id: str, event_time: datetime, temp: Optional[float], vib: Optional[float]) -> Tuple[str, str]:
    """
    Returns (exact_hash, semantic_hash).
    """
    exact = hashlib.sha256(f"{vendor.upper()}:{str(event_id).strip()}".encode()).hexdigest()
    
    t_round = round(temp, 1) if temp is not None else "none"
    v_round = round(vib, 1) if vib is not None else "none"
    semantic = hashlib.sha256(f"{machine_id}:{event_time.isoformat()}:{t_round}:{v_round}".encode()).hexdigest()
    
    return exact, semantic

def normalize_pulseforge_event(item: Dict[str, Any], default_plant_id: Optional[str], asset_catalog: Dict[str, Asset], job_id: str) -> CanonicalEvent:
    event_id = str(item.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("Missing event_id")

    machine_id = str(item.get("machine_id") or "").strip()
    if not machine_id:
        raise ValueError("Missing machine_id")

    # Timestamp
    event_time = parse_utc_timestamp(item.get("event_time"))

    # Asset lookup
    asset = asset_catalog.get(machine_id)
    plant_id = default_plant_id or (asset.plant_id if asset else "UNKNOWN_PLANT")
    line_id = normalize_line_id(item.get("line_id"), asset)

    # Telemetry
    raw_temp = item.get("temperature_c")
    temp_c = None
    if raw_temp is not None:
        try:
            temp_c = float(raw_temp)
            if temp_c < -50.0 or temp_c > 250.0:
                raise ValueError(f"Physical sensor temperature out of bounds: {temp_c}°C")
        except ValueError as e:
            raise ValueError(f"Invalid temperature_c: {raw_temp} ({str(e)})")

    raw_vib = item.get("vibration_mm_s")
    vib_mm_s = None
    if raw_vib is not None:
        try:
            vib_mm_s = float(raw_vib)
            if vib_mm_s < 0:
                raise ValueError(f"Negative vibration reading: {vib_mm_s}")
        except ValueError as e:
            raise ValueError(f"Invalid vibration_mm_s: {raw_vib} ({str(e)})")

    # Sensor health validation (must be 0.0 - 1.0)
    raw_sh = item.get("sensor_health")
    sensor_health = None
    if raw_sh is not None:
        try:
            sensor_health = float(raw_sh)
            if sensor_health < 0.0 or sensor_health > 1.0:
                raise ValueError(f"sensor_health out of range [0, 1]: {sensor_health}")
        except Exception:
            raise ValueError(f"Invalid non-numeric sensor_health: {raw_sh}")

    # Confidence validation
    raw_conf = item.get("vendor_confidence")
    vendor_conf = None
    if raw_conf is not None:
        try:
            vendor_conf = float(raw_conf)
            if vendor_conf < 0.0 or vendor_conf > 1.0:
                raise ValueError(f"vendor_confidence out of range [0, 1]: {vendor_conf}")
        except Exception:
            raise ValueError(f"Invalid non-numeric vendor_confidence: {raw_conf}")

    exact_hash, _ = calculate_dedup_hashes("PulseForge", event_id, machine_id, event_time, temp_c, vib_mm_s)

    # Machine state
    raw_state = str(item.get("machine_state") or "").upper()
    state = MachinePhysicalState.RUNNING.value if "RUN" in raw_state else (
        MachinePhysicalState.IDLE.value if "IDLE" in raw_state else (
            MachinePhysicalState.STOPPED.value if "STOP" in raw_state else MachinePhysicalState.RUNNING.value
        )
    )

    return CanonicalEvent(
        job_id=job_id,
        vendor="PulseForge",
        source_event_id=event_id,
        machine_id=machine_id,
        plant_id=plant_id,
        line_id=line_id,
        event_time=event_time,
        event_type=str(item.get("event_type") or "TELEMETRY").strip(),
        severity=str(item.get("severity") or "low").strip().lower(),
        vibration_mm_s=vib_mm_s,
        temperature_c=temp_c,
        power_kw=None,
        machine_state=state,
        sensor_health=sensor_health,
        vendor_confidence=vendor_conf,
        dedup_hash=exact_hash,
    )

def normalize_thermexwatch_reading(item: Dict[str, Any], default_site_code: Optional[str], asset_catalog: Dict[str, Asset], job_id: str) -> CanonicalEvent:
    reading_id = str(item.get("readingId") or "").strip()
    if not reading_id:
        raise ValueError("Missing readingId")

    asset_code = str(item.get("assetCode") or "").strip()
    if not asset_code:
        raise ValueError("Missing assetCode")

    event_time = parse_utc_timestamp(item.get("timestampMs"))

    asset = asset_catalog.get(asset_code)
    plant_id = default_site_code or (asset.plant_id if asset else "UNKNOWN_PLANT")
    line_id = normalize_line_id(item.get("productionLine"), asset)

    # Fahrenheit to Celsius conversion
    raw_temp_f = item.get("temperature_f")
    temp_c = None
    if raw_temp_f is not None:
        try:
            f = float(raw_temp_f)
            temp_c = round((f - 32.0) * 5.0 / 9.0, 2)
            if temp_c < -50.0 or temp_c > 250.0:
                raise ValueError(f"Physical sensor temperature out of bounds: {temp_c}°C ({f}°F)")
        except ValueError as e:
            raise ValueError(f"Invalid temperature_f: {raw_temp_f} ({str(e)})")

    # Vibration g to mm/s conversion (1g ≈ 15.6 mm/s at standard industrial frequency)
    raw_vib_g = item.get("vibration_g")
    vib_mm_s = None
    if raw_vib_g is not None:
        try:
            g = float(raw_vib_g)
            vib_mm_s = round(g * 15.6, 2)
        except ValueError as e:
            raise ValueError(f"Invalid vibration_g: {raw_vib_g} ({str(e)})")

    # Power
    raw_power = item.get("power_kw")
    power_kw = float(raw_power) if raw_power is not None else None

    # Alert level mapping (1 to 5)
    raw_level = item.get("level")
    try:
        level_int = int(raw_level) if raw_level is not None else 1
    except Exception:
        raise ValueError(f"Invalid non-integer level: {raw_level}")

    level_to_severity = {
        1: "low",
        2: "low",
        3: "medium",
        4: "high",
        5: "critical",
    }
    severity = level_to_severity.get(level_int, "medium")

    # State
    is_active = item.get("is_active")
    state = MachinePhysicalState.RUNNING.value if is_active is True else (
        MachinePhysicalState.STOPPED.value if is_active is False else MachinePhysicalState.UNKNOWN.value
    )

    # Quality
    signal_quality = str(item.get("signal_quality") or "").upper()
    sensor_health = 0.95 if signal_quality == "GOOD" else (0.75 if signal_quality == "FAIR" else 0.50)

    exact_hash, _ = calculate_dedup_hashes("ThermexWatch", reading_id, asset_code, event_time, temp_c, vib_mm_s)

    return CanonicalEvent(
        job_id=job_id,
        vendor="ThermexWatch",
        source_event_id=reading_id,
        machine_id=asset_code,
        plant_id=plant_id,
        line_id=line_id,
        event_time=event_time,
        event_type=str(item.get("alertCode") or "TELEMETRY").strip(),
        severity=severity,
        vibration_mm_s=vib_mm_s,
        temperature_c=temp_c,
        power_kw=power_kw,
        machine_state=state,
        sensor_health=sensor_health,
        vendor_confidence=0.85,
        dedup_hash=exact_hash,
    )

def normalize_maintaflow_record(item: Dict[str, Any], default_factory_id: Optional[str], asset_catalog: Dict[str, Asset], job_id: str) -> CanonicalEvent:
    record_id = str(item.get("record_id") or "").strip()
    if not record_id:
        raise ValueError("Missing record_id")

    machine_ref = str(item.get("machine_ref") or "").strip()
    if not machine_ref:
        raise ValueError("Missing machine_ref")

    event_time = parse_utc_timestamp(item.get("recorded_at"))

    asset = asset_catalog.get(machine_ref)
    plant_id = default_factory_id or (asset.plant_id if asset else "UNKNOWN_PLANT")
    line_id = normalize_line_id(item.get("line_ref"), asset)

    record_type = str(item.get("record_type") or "inspection").strip()
    inspection_result = item.get("inspection_result")
    maintenance_status = item.get("maintenance_status")
    technician_note = item.get("technician_note")

    # Map severity based on defect findings
    if inspection_result == "major_defect_found":
        severity = "critical"
    elif inspection_result == "minor_defect_found" or maintenance_status == "overdue":
        severity = "high"
    elif maintenance_status == "due_soon":
        severity = "medium"
    else:
        severity = "low"

    exact_hash, _ = calculate_dedup_hashes("MaintaFlow", record_id, machine_ref, event_time, None, None)

    return CanonicalEvent(
        job_id=job_id,
        vendor="MaintaFlow",
        source_event_id=record_id,
        machine_id=machine_ref,
        plant_id=plant_id,
        line_id=line_id,
        event_time=event_time,
        event_type=f"MAINTAFLOW_{record_type.upper()}",
        severity=severity,
        vibration_mm_s=None,
        temperature_c=None,
        power_kw=None,
        machine_state=None,
        sensor_health=1.0,
        vendor_confidence=0.90 if item.get("manual_confidence") == "high" else 0.70,
        record_type=record_type,
        maintenance_status=maintenance_status,
        inspection_result=inspection_result,
        technician_note=technician_note,
        dedup_hash=exact_hash,
    )
