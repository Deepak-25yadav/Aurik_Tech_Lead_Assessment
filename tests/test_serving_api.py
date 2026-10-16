import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_seed_and_serving_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Seed all data
        seed_res = await client.post("/api/v1/seed/load-all")
        assert seed_res.status_code == 200
        assert seed_res.json()["status"] == "SUCCESS"

        # 1. List machines
        machines_res = await client.get("/api/v1/machines")
        assert machines_res.status_code == 200
        machines = machines_res.json()
        assert len(machines) == 8

        # 2. Attention queue
        attention_res = await client.get("/api/v1/machines/attention")
        assert attention_res.status_code == 200
        att_machines = attention_res.json()
        assert len(att_machines) >= 1
        for m in att_machines:
            assert m["needs_attention"] is True

        # 3. Machine operational view
        eq1_res = await client.get("/api/v1/machines/EQ-001/operational-view")
        assert eq1_res.status_code == 200
        eq1 = eq1_res.json()
        assert eq1["machine_id"] == "EQ-001"
        assert "derived_status" in eq1
        assert "attention_level" in eq1
        assert "reason_codes" in eq1
        assert isinstance(eq1["reason_codes"], list)

        # 4. Plant summary
        plant_res = await client.get("/api/v1/plants/PLANT_01/summary")
        assert plant_res.status_code == 200
        p1 = plant_res.json()
        assert p1["plant_id"] == "PLANT_01"
        assert "machines_by_status" in p1
        assert "critical_machines" in p1
        assert "lines_requiring_attention_ranking" in p1

        # 5. Line summary
        line_res = await client.get("/api/v1/lines/LINE-A/summary")
        assert line_res.status_code == 200
        la = line_res.json()
        assert la["line_id"] == "LINE-A"
        assert la["operating_window"] == "day_shift"
        assert la["total_machines"] >= 2
