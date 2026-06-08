# C-MAPSS Turbofan Engine Digital Twin

A real-time interactive digital twin of a turbofan engine, trained on NASA's C-MAPSS FD001 run-to-failure dataset. Combines ML-based RUL prediction, LLM reasoning, graph-based health scoring, discrete-event maintenance simulation, and a feature-gated streaming telemetry pipeline.

---

## Features

| Feature | Description |
|---|---|
| **RUL Prediction** | Random Forest model trained on C-MAPSS data. Predicts Remaining Useful Life per cycle. |
| **LLM Engine Advisor** | Gemini-powered chat interface. Ask natural language questions about engine health and trends. |
| **Subsystem Health Graph** | NetworkX graph (Fleet → Engine → Subsystem → Sensor). Ranks degradation speed per subsystem. |
| **DTDL Contract Validation** | Azure Digital Twins Definition Language contract. Validates every tick against schema. |
| **Maintenance Scheduler** | SimPy discrete-event simulation. Triggers repair crew scheduling when predicted RUL < threshold. |
| **Telemetry Pipeline** | Feature-gated RabbitMQ (MQTT) → consumer → InfluxDB pipeline. App unchanged when flag is OFF. |
| **Engine Visualisation** | SVG schematic blocks + realistic engine cutaway overlay with per-subsystem health colouring. |
| **Playback Controls** | Play / Pause / Scrub through full engine lifetime cycle-by-cycle. Per-unit selection (1–100). |

---

## Project Structure

```
turbofan-engine-digital-twin/
├── app.py                    # Streamlit entry point
├── docker-compose.yml        # RabbitMQ + InfluxDB infrastructure
├── requirements.txt
├── docker/
│   └── rabbitmq_enabled_plugins
├── models/
│   ├── rul_model.joblib      # Trained RandomForest (auto-generated)
│   └── engine.dtdl.json      # DTDL contract schema
├── data/                     # C-MAPSS dataset (not committed)
├── assets/                   # Engine diagram image
└── twin/
    ├── config.py             # Feature flag: pipeline_active()
    ├── data_loader.py        # C-MAPSS loader, RUL computation, flat-sensor pruning
    ├── replay.py             # Row → state dict conversion
    ├── model.py              # RandomForest train/load/predict
    ├── llm.py                # Gemini prompt builder + API client
    ├── graph.py              # NetworkX subsystem health scoring
    ├── contract.py           # DTDL validation
    ├── maintenance.py        # SimPy maintenance event simulation
    ├── engine_svg.py         # SVG schematic renderer
    ├── engine_overlay.py     # Engine cutaway HTML overlay renderer
    ├── mqtt_io.py            # MQTT publish + subscribe (paho)
    ├── influx_io.py          # InfluxDB write + query
    └── consumer.py           # Standalone ingestion process
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose

### 2. Dataset

Download the [C-MAPSS FD001 dataset](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) and place the `*.txt` files in `data/`:

```
data/train_FD001.txt
data/test_FD001.txt
data/RUL_FD001.txt
```

### 3. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. API Key (LLM feature)

```bash
export GEMINI_API_KEY="your-gemini-key"
```

---

## Running the App (basic mode — no pipeline)

```bash
streamlit run app.py
```

The app runs fully in-memory. No Docker required.

---

## Running with Telemetry Pipeline (RabbitMQ + InfluxDB)

The pipeline is **feature-gated** — the app behaves identically without it.

### Step 1 — Start infrastructure

```bash
docker compose up -d
```

Services:
- RabbitMQ Management UI: http://localhost:15672 (guest / guest)
- InfluxDB UI: http://localhost:8086 (admin / password)

### Step 2 — Start the consumer

```bash
source .venv/bin/activate
python -m twin.consumer
```

The consumer subscribes to `twin/engine/telemetry` via MQTT and writes each message to InfluxDB.

### Step 3 — Run the app with pipeline enabled

```bash
TWIN_ENABLE_PIPELINE=1 streamlit run app.py
```

Or toggle **⚙️ Enable RabbitMQ+Influx pipeline** in the sidebar.

> **Note:** Scrubbing teleports to a single cycle. Use **▶️ Play** from cycle 0 to fill InfluxDB with the full trajectory.

---

## Pipeline Data Flow

```
Streamlit (app.py)
  └─► publish_state() via MQTT
        └─► RabbitMQ (amq.topic / twin/engine/telemetry)
              └─► consumer.py subscribes
                    └─► write_state() → InfluxDB
                          └─► query_recent() → Dashboard charts
```

When the pipeline flag is OFF, `chart_df` falls back to the in-memory `history_df` slice — no external dependency.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TWIN_ENABLE_PIPELINE` | `0` | Enable RabbitMQ + InfluxDB pipeline |
| `GEMINI_API_KEY` | — | Gemini API key for LLM chat |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB endpoint |
| `INFLUXDB_TOKEN` | `demo-token` | InfluxDB auth token |
| `INFLUXDB_ORG` | `demo-org` | InfluxDB organisation |
| `INFLUXDB_BUCKET` | `demo-bucket` | InfluxDB bucket |

---

## Credits

- Dataset: [NASA C-MAPSS](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) — Turbofan Engine Degradation Simulation Data Set
- Engine diagram: K. Aainsqatsi / Wikimedia Commons, [Turbofan operation.svg](https://commons.wikimedia.org/wiki/File:Turbofan_operation.svg), CC BY 2.5
