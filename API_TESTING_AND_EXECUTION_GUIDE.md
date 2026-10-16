# Industrial Equipment Monitoring API — Execution & Testing Guide

This document explains:
1. **Why the API was previously showing `ERR_CONNECTION_REFUSED`** and how the server is now running.
2. **How to start and verify the server from scratch** using terminal commands.
3. **Comprehensive Postman & cURL testing instructions** for all endpoints with exact HTTP Methods, URLs, Request Bodies, and Expected Responses.

---

## 1. Why `localhost:8000/health` Refused Connection

When you saw the browser error:
```
This site can’t be reached
localhost refused to connect.
ERR_CONNECTION_REFUSED
```
**Reason:** The automated test suite (`pytest`) ran tests in-memory without leaving a background server process alive. The web server daemon (`uvicorn`) had not been launched in a separate terminal window to listen on port 8000.

**Current Status:** The Uvicorn server is now actively running in the background listening on `http://0.0.0.0:8000`. You can now open **`http://localhost:8000/health`** or **`http://localhost:8000/docs`** directly in your browser.

---

## 2. How to Start the API from Terminal (From Scratch)

Whenever you restart your laptop or open a new terminal:

### Step 1: Open PowerShell in Project Directory
```powershell
cd c:\Users\deepa\OneDrive\Desktop\Aurik_Tech_Lead_Assessment
```

### Step 2: Start the Server Using the Automated Script
```powershell
.\run_local.ps1
```

*Or manually in two commands:*
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start Uvicorn HTTP Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Confirmation That Server is Live
You will see output like:
```text
INFO:     Started server process [21512]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Test it immediately in PowerShell:
```powershell
curl.exe http://localhost:8000/health
```
Response:
```json
{"status":"healthy","service":"Industrial Equipment Monitoring Platform","version":"1.0.0"}
```

---

## 3. Interactive Web Documentation (Swagger UI)

Open this URL in Google Chrome:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

This opens the interactive Swagger UI where you can test any endpoint by clicking **"Try it out"** and **"Execute"**.

---

## 4. Postman Step-by-Step Testing Guide

### How to Import the Provided Collection into Postman
1. Open **Postman**.
2. Click **Import** (top left).
3. Select the file: `c:\Users\deepa\OneDrive\Desktop\Aurik_Tech_Lead_Assessment\postman_collection.json`.
4. All endpoints below are pre-loaded and ready to click **Send**!

---

### Test 1: Service Health Check
* **Purpose**: Verify the backend server is reachable and healthy.
* **Method**: `GET`
* **URL**: `http://localhost:8000/health`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "status": "healthy",
  "service": "Industrial Equipment Monitoring Platform",
  "version": "1.0.0"
}
```

---

### Test 2: Ingest PulseForge Telemetry (Sync Mode)
* **Purpose**: Ingest high-vibration and temperature spike sensor events from PulseForge.
* **Method**: `POST`
* **URL**: `http://localhost:8000/api/v1/ingest/pulseforge?async=false`
* **Headers**: `Content-Type: application/json`
* **Body (raw JSON)**:
```json
{
  "vendor": "PulseForge",
  "plant_id": "PLANT_01",
  "batch_generated_at": "2026-04-18T08:05:00Z",
  "events": [
    {
      "event_id": "PF-9001",
      "machine_id": "EQ-001",
      "line_id": "LINE-A",
      "event_time": "2026-04-18T08:00:00Z",
      "event_type": "HIGH_VIBRATION",
      "severity": "high",
      "vibration_mm_s": 12.4,
      "temperature_c": 84.5,
      "machine_state": "running",
      "sensor_health": 0.92,
      "vendor_confidence": 0.88
    }
  ]
}
```
* **Expected Response (`202 Accepted`)**:
```json
{
  "status": "COMPLETED",
  "job_id": "3a7b6c8d-...",
  "vendor": "PulseForge",
  "records_total": 1,
  "records_processed": 1,
  "records_quarantined": 0,
  "records_duplicate": 0,
  "status_url": "/api/v1/ingestion/status/3a7b6c8d-..."
}
```

---

### Test 3: Ingest ThermexWatch Readings (Unit Conversion Test)
* **Purpose**: Tests normalization of Fahrenheit (°F) to Celsius (°C), $g$-force to $\text{mm/s}$, and numeric level (1–5).
* **Method**: `POST`
* **URL**: `http://localhost:8000/api/v1/ingest/thermexwatch?async=false`
* **Headers**: `Content-Type: application/json`
* **Body (raw JSON)**:
```json
{
  "source": "ThermexWatch",
  "site_code": "PLANT_01",
  "response_time_epoch_ms": 1776499560000,
  "readings": [
    {
      "readingId": "TW-9901",
      "assetCode": "EQ-002",
      "productionLine": "A",
      "timestampMs": 1776499152000,
      "alertCode": "TEMP_CRIT",
      "level": 5,
      "vibration_g": 0.85,
      "temperature_f": 208.4,
      "power_kw": 38.5,
      "is_active": true,
      "signal_quality": "GOOD"
    }
  ]
}
```
* **Expected Response (`202 Accepted`)**:
```json
{
  "status": "COMPLETED",
  "job_id": "b1c2d3e4-...",
  "vendor": "ThermexWatch",
  "records_total": 1,
  "records_processed": 1,
  "records_quarantined": 0,
  "records_duplicate": 0,
  "status_url": "/api/v1/ingestion/status/b1c2d3e4-..."
}
```
*(Notice: `208.4°F` is automatically converted to `98.0°C`, which breaches `EQ-002`'s rated limit of `90.0°C` and triggers `CRITICAL` status!)*

---

### Test 4: Ingest MaintaFlow Inspection (Defect Trigger)
* **Purpose**: Ingests qualitative maintenance report with a `major_defect_found`.
* **Method**: `POST`
* **URL**: `http://localhost:8000/api/v1/ingest/maintaflow?async=false`
* **Headers**: `Content-Type: application/json`
* **Body (raw JSON)**:
```json
{
  "provider_name": "MaintaFlow",
  "factory_id": "PLANT_02",
  "records": [
    {
      "record_id": "MF-9001",
      "machine_ref": "EQ-008",
      "line_ref": "LINE-E",
      "recorded_at": "2026/04/18 08:30:00",
      "record_type": "inspection",
      "inspection_result": "major_defect_found",
      "maintenance_status": "due_soon",
      "days_since_last_service": 21,
      "technician_note": "Drive belt frayed and loose; immediate replacement required",
      "manual_confidence": "high"
    }
  ]
}
```
* **Expected Response (`202 Accepted`)**:
```json
{
  "status": "COMPLETED",
  "job_id": "c4d5e6f7-...",
  "vendor": "MaintaFlow",
  "records_total": 1,
  "records_processed": 1,
  "records_quarantined": 0,
  "records_duplicate": 0,
  "status_url": "/api/v1/ingestion/status/c4d5e6f7-..."
}
```

---

### Test 5: Ingest Malformed Batch (Dead-Letter Queue Isolation Test)
* **Purpose**: Confirms that corrupted records (e.g. missing `machine_id`, invalid timestamp `"bad-ts"`) are quarantined to DLQ while the server remains healthy and operational.
* **Method**: `POST`
* **URL**: `http://localhost:8000/api/v1/ingest/batch?async=false`
* **Headers**: `Content-Type: application/json`
* **Body (raw JSON)**:
```json
{
  "pulseforge": {
    "vendor": "PulseForge",
    "plant_id": "PLANT_01",
    "events": [
      {
        "event_id": "PF-CORRUPT-1",
        "machine_id": "",
        "event_time": "2026-04-18T08:00:00Z",
        "event_type": "HIGH_VIBRATION"
      },
      {
        "event_id": "PF-CORRUPT-2",
        "machine_id": "EQ-001",
        "event_time": "bad-timestamp",
        "event_type": "TEMP_SPIKE"
      }
    ]
  }
}
```
* **Expected Response (`202 Accepted`)**:
```json
{
  "status": "FAILED",
  "job_id": "d8e9f0a1-...",
  "vendor": "multi_vendor_batch",
  "records_total": 2,
  "records_processed": 0,
  "records_quarantined": 2,
  "records_duplicate": 0,
  "status_url": "/api/v1/ingestion/status/d8e9f0a1-..."
}
```

---

### Test 6: Query Dead Letter Queue (DLQ)
* **Purpose**: Inspect the quarantined bad records and review the exact rejection reasons.
* **Method**: `GET`
* **URL**: `http://localhost:8000/api/v1/ingestion/dead-letter-queue`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "total_quarantined": 2,
  "records": [
    {
      "id": "...",
      "job_id": "...",
      "vendor": "PulseForge",
      "error_code": "RECORD_NORMALIZATION_FAILED",
      "error_reason": "Missing machine_id",
      "quarantined_at": "2026-10-16T14:10:00Z"
    },
    {
      "id": "...",
      "job_id": "...",
      "vendor": "PulseForge",
      "error_code": "RECORD_NORMALIZATION_FAILED",
      "error_reason": "Invalid timestamp format: 'bad-timestamp'",
      "quarantined_at": "2026-10-16T14:10:00Z"
    }
  ]
}
```

---

### Test 7: Machine Operational View (`EQ-001`)
* **Purpose**: Retrieve the derived operational status, severity, and explainable reason codes for a specific machine.
* **Method**: `GET`
* **URL**: `http://localhost:8000/api/v1/machines/EQ-001/operational-view`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "machine_id": "EQ-001",
  "plant_id": "PLANT_01",
  "line_id": "LINE-A",
  "derived_status": "NORMAL",
  "needs_attention": false,
  "attention_level": "NOMINAL",
  "reason_codes": [
    "RECOVERY_SIGNAL_VERIFIED (readings nominal)"
  ],
  "latest_relevant_event_time": "2026-04-18T08:32:05Z",
  "latest_temperature_c": 68.1,
  "latest_vibration_mm_s": 3.9,
  "latest_power_kw": 37.8,
  "latest_sensor_health": 0.95,
  "latest_machine_state": "RUNNING",
  "latest_inspection_result": "minor_defect_found",
  "latest_technician_note": "Belt wear visible; machine still operational",
  "source_event_refs": [
    "PF-1302",
    "PF-1301",
    "MF-501"
  ],
  "processing_status": "PROCESSED",
  "is_stale": false,
  "last_processed_at": "2026-10-16T14:10:00Z"
}
```

---

### Test 8: Machine Attention Priority Queue
* **Purpose**: Returns all machines currently requiring maintenance or attention, prioritized by severity (`CRITICAL` > `HIGH` > `MEDIUM`).
* **Method**: `GET`
* **URL**: `http://localhost:8000/api/v1/machines/attention`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
[
  {
    "machine_id": "EQ-008",
    "derived_status": "MAINTENANCE_REQUIRED",
    "attention_level": "CRITICAL",
    "needs_attention": true,
    "reason_codes": [
      "OPEN_WORK_ORDER (WO-1003: heat_shield)",
      "MAJOR_INSPECTION_DEFECT_ACTIVE - Heat shield loose; monitor continuously"
    ]
  },
  {
    "machine_id": "EQ-002",
    "derived_status": "CRITICAL",
    "attention_level": "CRITICAL",
    "needs_attention": true,
    "reason_codes": [
      "OPEN_WORK_ORDER (WO-1001: cooling_system)",
      "OVER_TEMPERATURE_CRITICAL (97.0°C > rated max 90.0°C)"
    ]
  },
  {
    "machine_id": "EQ-005",
    "derived_status": "WARNING",
    "attention_level": "HIGH",
    "needs_attention": true,
    "reason_codes": [
      "EXCESSIVE_VIBRATION (8.4 mm/s > rated max 8.0 mm/s)"
    ]
  }
]
```

---

### Test 9: Plant-Level Summary (`PLANT_01`)
* **Purpose**: Aggregated overview of plant operational health, status counts, critical machines, and line ranking.
* **Method**: `GET`
* **URL**: `http://localhost:8000/api/v1/plants/PLANT_01/summary`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "plant_id": "PLANT_01",
  "total_machines": 4,
  "machines_by_status": {
    "NORMAL": 3,
    "CRITICAL": 1
  },
  "machines_requiring_attention": 1,
  "critical_machines": [
    "EQ-002"
  ],
  "lines_requiring_attention_ranking": [
    {
      "line_id": "LINE-A",
      "machines_needing_attention": 1
    }
  ],
  "stale_machines_count": 0
}
```

---

### Test 10: Production Line Summary (`LINE-A`)
* **Purpose**: Line-specific equipment health and operating window summary.
* **Method**: `GET`
* **URL**: `http://localhost:8000/api/v1/lines/LINE-A/summary`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "line_id": "LINE-A",
  "plant_id": "PLANT_01",
  "line_name": "Assembly",
  "operating_window": "day_shift",
  "total_machines": 2,
  "machines_by_status": {
    "NORMAL": 1,
    "CRITICAL": 1
  },
  "machines_requiring_attention": 1,
  "critical_machines": [
    "EQ-002"
  ]
}
```

---

### Test 11: Ingest All Seed Datasets (One-Click Live Demo)
* **Purpose**: Ingests all CSV seed files in `seed_data/` and refreshes all machines.
* **Method**: `POST`
* **URL**: `http://localhost:8000/api/v1/seed/load-all`
* **Headers**: None
* **Body**: None
* **Expected Response (`200 OK`)**:
```json
{
  "status": "SUCCESS",
  "message": "All seed reference catalogs and vendor batches ingested successfully.",
  "results": {
    "pulseforge": {
      "status": "COMPLETED",
      "processed": 8,
      "quarantined": 0
    },
    "thermexwatch": {
      "status": "COMPLETED",
      "processed": 7,
      "quarantined": 0
    },
    "maintaflow": {
      "status": "COMPLETED",
      "processed": 6,
      "quarantined": 0
    }
  }
}
```
