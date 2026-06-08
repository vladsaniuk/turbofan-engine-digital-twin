# Architecture — C-MAPSS Turbofan Engine Digital Twin

## System Overview

The system has two operating modes controlled by a single feature flag (`TWIN_ENABLE_PIPELINE`):

- **Flag OFF (default):** Fully self-contained Streamlit app. All data comes from in-memory replay of C-MAPSS CSV data.
- **Flag ON:** Streaming telemetry pipeline activates. App publishes each tick to RabbitMQ; a standalone consumer persists data to InfluxDB; dashboard reads back from InfluxDB.

---

## Component Map

```mermaid
graph TD
    subgraph "Data Layer"
        CSV["C-MAPSS FD001 Dataset\n(data/*.txt)"]
        MODEL["RandomForest Model\n(models/rul_model.joblib)"]
        DTDL["DTDL Contract\n(models/engine.dtdl.json)"]
    end

    subgraph "Twin Core (twin/)"
        DL["data_loader.py\nload_raw · compute_rul\ndrop_flat_sensors · get_unit"]
        RPL["replay.py\nrow_to_state()"]
        MDL["model.py\ntrain_model · load_or_train\npredict_rul"]
        GRP["graph.py\nbuild_graph · subsystem_health\nNetworkX DiGraph"]
        CTR["contract.py\nvalidate_row · DTDL check"]
        MNT["maintenance.py\nevaluate_maintenance\nSimPy discrete-event"]
        LLM["llm.py\nask_twin · state_to_prompt\nGemini API"]
        SVG["engine_svg.py\nrender_engine_svg"]
        OVL["engine_overlay.py\nrender_engine_overlay"]
        CFG["config.py\npipeline_active()"]
    end

    subgraph "Telemetry Pipeline (feature-gated)"
        MQTT["mqtt_io.py\npublish_state · start_subscriber\npaho-mqtt"]
        INFLX["influx_io.py\nwrite_state · query_recent\ninfluxdb-client"]
        CONS["consumer.py\nstandalone process"]
        RMQ[("RabbitMQ\n:1883 MQTT\n:15672 UI")]
        IDB[("InfluxDB 2.7\n:8086")]
    end

    subgraph "Presentation"
        APP["app.py\nStreamlit Dashboard"]
    end

    CSV --> DL
    DL --> RPL
    RPL --> APP
    DL --> MDL
    MDL --> MODEL
    MODEL --> APP
    GRP --> APP
    CTR --> DTDL
    CTR --> APP
    MNT --> APP
    LLM --> APP
    SVG --> APP
    OVL --> APP
    CFG --> APP

    APP -- "pipeline_active()" --> MQTT
    MQTT -- "publish_state()" --> RMQ
    RMQ -- "MQTT subscribe" --> CONS
    CONS --> INFLX
    INFLX --> IDB
    IDB -- "query_recent()" --> APP
```

---

## Data Flow

### Mode A — In-Memory Replay (pipeline OFF)

```mermaid
sequenceDiagram
    participant User
    participant App as app.py
    participant DL as data_loader
    participant MDL as model.py
    participant GRP as graph.py
    participant LLM as llm.py

    User->>App: move Scrub slider / Play
    App->>DL: get_unit(unit_id)
    DL-->>App: history_df (CSV slice)
    App->>MDL: predict_rul(model, current_state)
    MDL-->>App: predicted_RUL
    App->>GRP: subsystem_health(state, history_df)
    GRP-->>App: sub_scores {LPC, HPC, Fan, ...}
    App->>User: render charts + metrics
    User->>App: ask question
    App->>LLM: ask_twin(question, state, history_df)
    LLM-->>App: Gemini answer
    App->>User: chat response
```

### Mode B — Streaming Pipeline (pipeline ON)

```mermaid
sequenceDiagram
    participant App as app.py
    participant MQTT as mqtt_io
    participant RMQ as RabbitMQ
    participant CONS as consumer.py
    participant INFLX as influx_io
    participant IDB as InfluxDB

    Note over App: Per Streamlit tick (Play or Scrub)
    App->>MQTT: publish_state(current_state)
    MQTT->>RMQ: MQTT publish (twin/engine/telemetry)
    RMQ->>CONS: on_message callback
    CONS->>INFLX: write_state(state)
    INFLX->>IDB: InfluxDB Point write
    App->>INFLX: query_recent(unit_id)
    INFLX->>IDB: Flux query (last 30d, pivot)
    IDB-->>INFLX: DataFrame
    INFLX-->>App: chart_df
    App->>App: filter cycles ≤ current_cycle
    App->>App: render charts from InfluxDB data
```

---

## Module Reference

### `twin/data_loader.py`
Loads and preprocesses the C-MAPSS dataset:
- `load_raw()` — reads whitespace-separated `.txt` file, assigns 26 column names.
- `compute_rul()` — calculates RUL as `max_cycle_per_unit - cycle`.
- `find_flat_sensors()` / `drop_flat_sensors()` — removes constant sensors (std ≤ 1e-6). Drops: sensor_1, 5, 10, 16, 18, 19.
- `get_unit(unit_id)` — full pipeline for a single engine unit.

### `twin/replay.py`
Converts a DataFrame row to the canonical `state` dict used across all modules:
```python
{
  "unit_id": int,
  "cycle": int,
  "RUL": int,
  "settings": {"op_setting_1": ..., "op_setting_2": ..., "op_setting_3": ...},
  "sensors": {"sensor_2": ..., "sensor_3": ..., ...}
}
```

### `twin/model.py`
RandomForest RUL predictor:
- Trains on C-MAPSS units 1–100 with RUL capped at 130.
- Uses `model.feature_names_in_` to enforce column order on inference (guards against InfluxDB column reordering).
- Auto-trains on first run; cached to `models/rul_model.joblib`.

### `twin/graph.py`
NetworkX directed graph: `Fleet → Engine_{id} → Subsystem → Sensor`.
`subsystem_health()` computes per-subsystem degradation score as mean % drift of member sensors over the last 20 cycles.

Subsystem mapping:
| Subsystem | Sensors |
|---|---|
| Fan | sensor_6, sensor_8, sensor_13, sensor_15 |
| HPC | sensor_3, sensor_7, sensor_9, sensor_11, sensor_14 |
| LPC | sensor_2 |
| LPT | sensor_4, sensor_21 |
| HPT | sensor_17, sensor_20 |
| Combustor | sensor_12 |

### `twin/contract.py`
Validates the current state dict against the DTDL schema (`models/engine.dtdl.json`). Checks all `Telemetry` and `Property` fields are present and finite. Maps raw `sensor_N` keys to DTDL names via `SENSOR_DTDL_MAP`.

### `twin/maintenance.py`
SimPy discrete-event simulation. When `predicted_rul < threshold`:
1. Generates a maintenance request.
2. Acquires a crew resource (capacity = 1).
3. Runs a 4-hour repair process.
4. Returns event log + urgency level (`High` / `Critical`).

### `twin/llm.py`
Builds a compact JSON prompt (current state + last 10 cycles history + subsystem scores) and sends to Gemini API (`gemini-3.1-flash-lite`). System prompt constrains the model to act as the digital twin.

### `twin/config.py`
Single source of truth for the pipeline feature flag. Checks `st.session_state.pipeline_enabled` first, falls back to `TWIN_ENABLE_PIPELINE` env var.

### `twin/mqtt_io.py`
- `publish_state()` — uses `paho.mqtt.publish.single()` (blocking — waits for message to fly before returning).
- `start_subscriber()` — blocking `loop_forever()` subscriber for the consumer process.

### `twin/influx_io.py`
- `write_state()` — writes one `engine_telemetry` Point per tick. Tags: `unit_id`. Fields: all sensors, settings, cycle, RUL.
- `query_recent()` — Flux query with pivot (field → column), sorted ascending by cycle.

### `twin/consumer.py`
Standalone process. Run separately from Streamlit. Subscribes to MQTT, calls `write_state()` on each message. Robust `try/except` per message.

---

## Infrastructure (docker-compose.yml)

```mermaid
graph LR
    subgraph Docker
        RMQ["rabbitmq:3-management\n1883 MQTT · 15672 Admin · 5672 AMQP"]
        IDB["influxdb:2.7\n8086 HTTP API + UI"]
    end
    subgraph Host
        APP["app.py\n:8501"]
        CONS["consumer.py"]
    end
    APP -- ":1883" --> RMQ
    CONS -- ":1883" --> RMQ
    CONS -- ":8086" --> IDB
    APP -- ":8086" --> IDB
```

RabbitMQ MQTT plugin enabled via `docker/rabbitmq_enabled_plugins`:
```
[rabbitmq_management,rabbitmq_mqtt].
```

---

## Feature Flag Design

The pipeline is **additive and fully isolated**. When `TWIN_ENABLE_PIPELINE=0` (default):
- No `import` of `mqtt_io` or `influx_io` executes at module level.
- `chart_df` stays as `history_df` (in-memory CSV slice).
- Zero UI difference.

When enabled, every new code path is inside `if pipeline_active():` blocks.
