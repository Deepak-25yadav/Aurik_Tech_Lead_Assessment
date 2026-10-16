from typing import List, Optional, Any
from pydantic import BaseModel, Field

class MaintaFlowRecordItem(BaseModel):
    record_id: Any
    machine_ref: Any
    line_ref: Optional[Any] = None
    recorded_at: Any
    record_type: Optional[Any] = None
    inspection_result: Optional[Any] = None
    maintenance_status: Optional[Any] = None
    days_since_last_service: Optional[Any] = None
    technician_note: Optional[Any] = None
    manual_confidence: Optional[Any] = None

class MaintaFlowPayload(BaseModel):
    provider_name: str = "MaintaFlow"
    factory_id: Optional[str] = None
    records: List[MaintaFlowRecordItem] = Field(default_factory=list)
