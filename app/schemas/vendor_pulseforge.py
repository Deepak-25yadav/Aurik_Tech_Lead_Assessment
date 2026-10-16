from typing import List, Optional, Any
from pydantic import BaseModel, Field

class PulseForgeEventItem(BaseModel):
    event_id: Any
    machine_id: Any
    line_id: Optional[Any] = None
    event_time: Any
    event_type: Any
    severity: Any
    vibration_mm_s: Optional[Any] = None
    temperature_c: Optional[Any] = None
    machine_state: Optional[Any] = None
    sensor_health: Optional[Any] = None
    vendor_confidence: Optional[Any] = None

class PulseForgePayload(BaseModel):
    vendor: str = "PulseForge"
    plant_id: Optional[str] = None
    batch_generated_at: Optional[Any] = None
    events: List[PulseForgeEventItem] = Field(default_factory=list)
