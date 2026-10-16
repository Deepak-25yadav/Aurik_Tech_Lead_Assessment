from typing import List, Optional, Any
from pydantic import BaseModel, Field

class ThermexWatchReadingItem(BaseModel):
    readingId: Any
    assetCode: Any
    productionLine: Optional[Any] = None
    timestampMs: Any
    alertCode: Optional[Any] = None
    level: Optional[Any] = None
    vibration_g: Optional[Any] = None
    temperature_f: Optional[Any] = None
    power_kw: Optional[Any] = None
    is_active: Optional[Any] = None
    signal_quality: Optional[Any] = None

class ThermexWatchPayload(BaseModel):
    source: str = "ThermexWatch"
    site_code: Optional[str] = None
    response_time_epoch_ms: Optional[Any] = None
    readings: List[ThermexWatchReadingItem] = Field(default_factory=list)
