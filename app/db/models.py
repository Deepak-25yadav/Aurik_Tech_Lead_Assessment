import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    Index,
)
from app.db.base import Base
from app.core.constants import (
    DerivedStatus,
    AttentionLevel,
    MachinePhysicalState,
    IngestionJobStatus,
)

def utc_now():
    return datetime.now(timezone.utc)

class ProductionLine(Base):
    __tablename__ = "production_lines"

    line_id = Column(String(50), primary_key=True)
    plant_id = Column(String(50), nullable=False, index=True)
    line_name = Column(String(100), nullable=False)
    operating_window = Column(String(50), nullable=False)

class Asset(Base):
    __tablename__ = "assets"

    machine_id = Column(String(50), primary_key=True)
    plant_id = Column(String(50), nullable=False, index=True)
    line_id = Column(String(50), nullable=False, index=True)
    machine_type = Column(String(100), nullable=False)
    criticality = Column(String(20), nullable=False)  # high, medium, low
    installed_date = Column(String(20), nullable=True)
    rated_max_temp_c = Column(Float, nullable=False, default=85.0)
    rated_max_vibration_mm_s = Column(Float, nullable=False, default=8.5)
    baseline_power_kw = Column(Float, nullable=False, default=25.0)
    asset_status = Column(String(50), nullable=False, default="active")  # active, maintenance

class MaintenanceWorkOrder(Base):
    __tablename__ = "maintenance_work_orders"

    work_order_id = Column(String(50), primary_key=True)
    plant_id = Column(String(50), nullable=False, index=True)
    machine_id = Column(String(50), nullable=False, index=True)
    line_id = Column(String(50), nullable=False)
    opened_at = Column(String(50), nullable=False)
    closed_at = Column(String(50), nullable=True)
    maintenance_type = Column(String(100), nullable=False)
    trigger_source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, index=True)  # open, closed
    downtime_minutes = Column(Integer, default=0)
    post_maintenance_check = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False, default=IngestionJobStatus.PENDING.value, index=True)
    records_total = Column(Integer, nullable=False, default=0)
    records_processed = Column(Integer, nullable=False, default=0)
    records_quarantined = Column(Integer, nullable=False, default=0)
    records_duplicate = Column(Integer, nullable=False, default=0)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class RawIngestionLog(Base):
    __tablename__ = "raw_ingestion_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), nullable=False, index=True)
    vendor = Column(String(50), nullable=False)
    received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    raw_payload = Column(Text, nullable=False)
    record_count = Column(Integer, default=0)

class CanonicalEvent(Base):
    __tablename__ = "canonical_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), nullable=False, index=True)
    vendor = Column(String(50), nullable=False, index=True)
    source_event_id = Column(String(100), nullable=False)
    machine_id = Column(String(50), nullable=False, index=True)
    plant_id = Column(String(50), nullable=False, index=True)
    line_id = Column(String(50), nullable=False, index=True)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    event_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    vibration_mm_s = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    power_kw = Column(Float, nullable=True)
    machine_state = Column(String(50), nullable=True)
    sensor_health = Column(Float, nullable=True)
    vendor_confidence = Column(Float, nullable=True)
    
    # Maintenance / Inspection enrichments
    record_type = Column(String(50), nullable=True)
    maintenance_status = Column(String(50), nullable=True)
    inspection_result = Column(String(100), nullable=True)
    technician_note = Column(Text, nullable=True)
    
    # Deduplication Fingerprint
    dedup_hash = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index("idx_machine_time", "machine_id", "event_time"),
    )

class MachineOperationalState(Base):
    __tablename__ = "machine_operational_states"

    machine_id = Column(String(50), primary_key=True, index=True)
    plant_id = Column(String(50), nullable=False, index=True)
    line_id = Column(String(50), nullable=False, index=True)
    
    derived_status = Column(String(50), nullable=False, default=DerivedStatus.UNKNOWN.value)
    needs_attention = Column(Boolean, nullable=False, default=False)
    attention_level = Column(String(50), nullable=False, default=AttentionLevel.NOMINAL.value)
    reason_codes = Column(JSON, nullable=False, default=list)
    
    latest_relevant_event_time = Column(DateTime(timezone=True), nullable=True)
    latest_temperature_c = Column(Float, nullable=True)
    latest_vibration_mm_s = Column(Float, nullable=True)
    latest_power_kw = Column(Float, nullable=True)
    latest_sensor_health = Column(Float, nullable=True)
    latest_machine_state = Column(String(50), nullable=True, default=MachinePhysicalState.UNKNOWN.value)
    latest_inspection_result = Column(String(100), nullable=True)
    latest_technician_note = Column(Text, nullable=True)
    
    source_event_refs = Column(JSON, nullable=False, default=list)
    processing_status = Column(String(50), nullable=False, default="PROCESSED")
    is_stale = Column(Boolean, nullable=False, default=False)
    last_processed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class DeadLetterRecord(Base):
    __tablename__ = "dead_letter_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), nullable=False, index=True)
    vendor = Column(String(50), nullable=False)
    raw_record = Column(Text, nullable=False)
    error_code = Column(String(100), nullable=False)
    error_reason = Column(Text, nullable=False)
    quarantined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
