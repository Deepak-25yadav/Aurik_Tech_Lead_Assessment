import pytest
import json
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

DATA_DIR = Path(__file__).resolve().parent.parent

@pytest.mark.asyncio
async def test_pulseforge_ingestion_sync():
    with open(DATA_DIR / "vendor_api_samples" / "pulseforge_sample.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test synchronous execution for deterministic assertions
        response = await client.post("/api/v1/ingest/pulseforge?async=false", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["vendor"] == "PulseForge"
        assert data["records_total"] == 2
        assert data["records_processed"] >= 0

        # Query job status
        job_id = data["job_id"]
        status_res = await client.get(f"/api/v1/ingestion/status/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ["COMPLETED", "PARTIAL_SUCCESS"]

@pytest.mark.asyncio
async def test_thermexwatch_ingestion_sync():
    with open(DATA_DIR / "vendor_api_samples" / "thermexwatch_sample.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/thermexwatch?async=false", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["vendor"] == "ThermexWatch"
        assert data["records_total"] == 2

@pytest.mark.asyncio
async def test_maintaflow_ingestion_sync():
    with open(DATA_DIR / "vendor_api_samples" / "maintaflow_sample.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/maintaflow?async=false", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["vendor"] == "MaintaFlow"
        assert data["records_total"] == 2

@pytest.mark.asyncio
async def test_batch_ingestion_async():
    with open(DATA_DIR / "vendor_api_samples" / "happy_path.json", "r") as f:
        payload = json.load(f)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/batch?async=true", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "ACCEPTED"
        assert "job_id" in data
