from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CanonicalEventSchema(BaseModel):
    id: Optional[str] = None
    job_id: str
    vendor: str
    source_event_id: str
    machine_id: str
    plant_id: str
    line_id: str
    event_time: datetime
    ingested_at: datetime
    
    event_type: str
    severity: str
    vibration_mm_s: Optional[float] = None
    temperature_c: Optional[float] = None
    power_kw: Optional[float] = None
    machine_state: Optional[str] = None
    sensor_health: Optional[float] = None
    vendor_confidence: Optional[float] = None
    
    record_type: Optional[str] = None
    maintenance_status: Optional[str] = None
    inspection_result: Optional[str] = None
    technician_note: Optional[str] = None
    dedup_hash: str

    model_config = {
        "from_attributes": True
    }

class MachineOperationalViewResponse(BaseModel):
    machine_id: str
    plant_id: str
    line_id: str
    derived_status: str
    needs_attention: bool
    attention_level: str
    reason_codes: List[str]
    latest_relevant_event_time: Optional[datetime] = None
    latest_temperature_c: Optional[float] = None
    latest_vibration_mm_s: Optional[float] = None
    latest_power_kw: Optional[float] = None
    latest_sensor_health: Optional[float] = None
    latest_machine_state: Optional[str] = None
    latest_inspection_result: Optional[str] = None
    latest_technician_note: Optional[str] = None
    source_event_refs: List[str] = Field(default_factory=list)
    processing_status: str
    is_stale: bool
    last_processed_at: datetime

    model_config = {
        "from_attributes": True
    }

class PlantSummaryResponse(BaseModel):
    plant_id: str
    total_machines: int
    machines_by_status: dict[str, int]
    machines_requiring_attention: int
    critical_machines: List[str]
    lines_summary: List[dict]
    stale_machines_count: int

class LineSummaryResponse(BaseModel):
    line_id: str
    plant_id: str
    line_name: str
    operating_window: str
    total_machines: int
    machines_by_status: dict[str, int]
    machines_requiring_attention: int
    critical_machines: List[str]
