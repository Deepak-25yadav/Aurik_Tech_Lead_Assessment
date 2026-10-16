# Industrial Equipment Monitoring Backend — Engineering Design Note

**Candidate:** Deepak Yadav  
**Role:** Founding Tech Lead  
**Company:** Aurik Technologies  
**Date:** October 2026  

---

## 1. System Overview & Problem Context

In industrial manufacturing, equipment health data arrives from a fragmented landscape of sensors, IoT gateways, and maintenance management platforms:
- **PulseForge**: Modern sensor stream reporting temperature in Celsius (°C), vibration in velocity ($\text{mm/s}$), and ISO 8601 UTC timestamps.
- **ThermexWatch**: Legacy gateway reporting temperatures in Fahrenheit (°F), vibration acceleration in $g$-force, numeric alert levels (1–5), and epoch milliseconds.
- **MaintaFlow**: Qualitative operational log reporting maintenance work orders, inspection results (`major_defect_found`, `minor_defect_found`), and operator notes.

The primary architectural challenge is to ingest this high-velocity, malformed, and out-of-order telemetry without system downtime, normalize it into a unified canonical model, preserve auditability, and deterministically compute an explainable **Machine Operational Attention View**.

---

## 2. Core Architectural Decisions

### 2.1 Technology Stack Selection
- **FastAPI (Python 3.14 / 3.12)**: Selected for asynchronous I/O capability, automatic OpenAPI contract generation, and native integration with Pydantic v2.
- **Pydantic v2**: Provides ultra-fast schema boundary validation and type coercion.
- **SQLAlchemy 2.0 (Async) + SQLite**: Eliminates external infrastructure dependencies (such as managed PostgreSQL or Redis) for take-home review while adopting the exact async repository patterns required for zero-code-change migration to PostgreSQL in production.
- **FastAPI BackgroundTasks & Decoupled Pipeline**: Ingestion endpoints return `HTTP 202 Accepted` with a `job_id` within milliseconds, offloading intensive normalization and state calculation to background workers.

---

## 3. Data Ingestion & Fault Isolation (Dead-Letter Queue)

### 3.1 Batch Processing Strategy
Industrial batches often contain mixed-quality records. A naive implementation rejects the entire batch if one record has an invalid timestamp or corrupt value. Our system processes records independently within an isolated transactional boundary:
- **Valid records**: Normalized, deduplicated, and persisted to `canonical_events`.
- **Corrupt / Malformed records**: Diverted to `dead_letter_records` (quarantine) with an explicit error code (e.g. `MISSING_MACHINE_ID`, `INVALID_TIMESTAMP`, `PHYSICAL_BOUNDS_EXCEEDED`) and the verbatim raw payload.
- **Ingestion Job Status**: Marked as `PARTIAL_SUCCESS` if any records are quarantined, or `COMPLETED` if all records succeed.

### 3.2 Deduplication & Idempotency
We implement two-tier deduplication:
1. **Exact Deduplication**: SHA-256 hash of `vendor + source_event_id`. Duplicate deliveries of the same vendor payload trigger no-op idempotent bypasses.
2. **Semantic Deduplication**: SHA-256 hash of `machine_id + event_time_utc + round(temperature, 1) + round(vibration, 1)`. Identical readings sent by retransmitting gateways under different message identifiers are detected and recorded under `records_duplicate`.

---

## 4. Normalization Engine

### 4.1 Unit Standardization
- **Temperature**: Normalized to Celsius (°C):
  $$T_c = \frac{(T_f - 32) \times 5}{9}$$
  Physical plausibility check rejects readings outside $[-50^\circ\text{C}, 250^\circ\text{C}]$, cleanly intercepting sensor fault codes like `-999`.
- **Vibration**: ThermexWatch $g$-force acceleration is converted to equivalent peak velocity ($\text{mm/s}$) using standard industrial vibration velocity mapping ($1g \approx 15.6\,\text{mm/s}$ at 50Hz nominal rotational frequency), enabling direct threshold comparison against machine rated maximums (`rated_max_vibration_mm_s`).

### 4.2 Timestamp Standardization
Supports multi-vendor formats (epoch milliseconds, epoch seconds, ISO 8601 strings, and legacy formatted dates) normalized into timezone-aware UTC `datetime` instances.

### 4.3 Entity Resolution
Production lines (`"A"`, `"LINE-A"`) are resolved to canonical identifier `LINE-A`. Unknown machines are validated against the `asset_reference` catalog.

---

## 5. Deterministic Operational Derivation vs. Black-Box ML

### Why Deterministic Logic is Preferred
In manufacturing equipment health monitoring, deterministic, rule-based derivation is vastly superior to black-box machine learning for baseline operational decisions:
1. **Safety Compliance**: Plant operators require absolute certainty why a machine was flagged `CRITICAL`.
2. **Explainability**: Maintenance crews need human-actionable reason codes (e.g. `OVER_TEMPERATURE_CRITICAL (96.4°C > rated 90.0°C)` or `OPEN_WORK_ORDER: cooling_system`).
3. **Multi-Signal Conflict Resolution**: When PulseForge sends `RECOVERY_SIGNAL` but MaintaFlow records `major_defect_found` (e.g., loose heat shield), a statistical model might average these out to "nominal"; our deterministic engine enforces a safety hierarchy where physical inspection defects override automated recovery signals.

---

## 6. Distributed Scalability & Production Roadmap

For high-scale multi-plant deployment:
1. **Message Broker**: Swap in-memory `BackgroundTasks` with Apache Kafka or RabbitMQ partitioned by `plant_id` / `machine_id` for horizontal scaling and guaranteed delivery.
2. **Time-Series Storage**: Route high-frequency normalized sensor telemetry into TimescaleDB or ClickHouse, keeping PostgreSQL for asset metadata and derived operational states.
3. **Distributed Caching**: Cache `MachineOperationalState` in Redis with pub/sub invalidation to serve million-QPS dashboard requests under 5ms.
4. **Out-of-Order Watermarking**: Implement tumbling or sliding time windows with a watermark (e.g. 5 minutes) to handle late-arriving IoT telemetry from intermittent factory connectivity.

---

## 7. AI Usage Disclosure (Candidate Brief Section 10)

In accordance with Section 10 of the Candidate Brief:
- **Tools Used**: Antigravity AI IDE / Google Gemini 3.8.
- **How Used**: Used as an interactive pair-programming companion for scaffolding boilerplates, generating exhaustive test cases across edge-case JSON batches, and assisting in structured documentation formatting.
- **Independent Candidate Decisions**: Architecture blueprint, deterministic severity rules, unit conversion constants, deduplication hashing design, database relational schema, and error isolation quarantine mechanisms are authored and verified directly by the candidate.
