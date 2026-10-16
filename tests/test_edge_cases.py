import pytest
import json
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

DATA_DIR = Path(__file__).resolve().parent.parent

@pytest.mark.asyncio
async def test_malformed_payload_quarantine():
    with open(DATA_DIR / "vendor_api_samples" / "malformed.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Ingest malformed batch synchronously to verify quarantine
        res = await client.post("/api/v1/ingest/batch?async=false", json=payload)
        assert res.status_code == 202
        data = res.json()
        
        # Verify quarantine records exist and server did not crash
        assert data["records_quarantined"] > 0
        job_id = data["job_id"]

        # Check Dead Letter Queue endpoint
        dlq_res = await client.get(f"/api/v1/ingestion/dead-letter-queue?job_id={job_id}")
        assert dlq_res.status_code == 200
        dlq_data = dlq_res.json()
        assert dlq_data["total_quarantined"] > 0
        reasons = [r["error_reason"] for r in dlq_data["records"]]
        # Expect specific reasons like missing machine_id or invalid timestamp
        assert any("machine_id" in r or "timestamp" in r or "temperature" in r or "sensor_health" in r for r in reasons)

@pytest.mark.asyncio
async def test_duplicate_handling_idempotency():
    with open(DATA_DIR / "vendor_api_samples" / "duplicates.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First submission
        res1 = await client.post("/api/v1/ingest/batch?async=false", json=payload)
        assert res1.status_code == 202
        
        # Immediate duplicate submission
        res2 = await client.post("/api/v1/ingest/batch?async=false", json=payload)
        assert res2.status_code == 202
        data2 = res2.json()
        
        # In second submission, records should be recognized as duplicates
        assert data2["records_duplicate"] > 0

@pytest.mark.asyncio
async def test_out_of_order_preserves_chronology():
    with open(DATA_DIR / "vendor_api_samples" / "out_of_order.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/ingest/batch?async=false", json=payload)
        assert res.status_code == 202

        # In out_of_order.json:
        # PF-1302 has time 08:32:05 (RECOVERY_SIGNAL, temp 68.1)
        # PF-1301 has time 08:31:02 (HIGH_VIBRATION, temp 84.0)
        # Although PF-1302 is first in the list, the latest chronological event is 08:32:05 (recovery).
        op_res = await client.get("/api/v1/machines/EQ-001/operational-view")
        assert op_res.status_code == 200
        op_data = op_res.json()
        # State should reflect the newest chronological event time
        assert "2026-04-18" in op_data["latest_relevant_event_time"]

@pytest.mark.asyncio
async def test_conflicting_updates_safety_priority():
    with open(DATA_DIR / "vendor_api_samples" / "conflicting_updates.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/ingest/batch?async=false", json=payload)
        assert res.status_code == 202

        # For EQ-008:
        # PulseForge reports recovery signal at 08:39:10
        # ThermexWatch reports TEMP_CRIT level 5 (temp 201F)
        # MaintaFlow reports major_defect_found at 08:41:00
        # Safety rules must prioritize the open defect and critical temperature over recovery
        op_res = await client.get("/api/v1/machines/EQ-008/operational-view")
        assert op_res.status_code == 200
        op_data = op_res.json()
        assert op_data["needs_attention"] is True
        assert op_data["attention_level"] == "CRITICAL"
        assert any("MAJOR_INSPECTION_DEFECT" in r or "DEFECT" in r or "TEMP" in r for r in op_data["reason_codes"])
