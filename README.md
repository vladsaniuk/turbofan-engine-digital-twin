# C-MAPSS Digital Twin

## Structure

- `data/` — dataset goes here.
- `twin/` — twin logic and API tests.
- `app.py` — Streamlit entry point.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

```bash
streamlit run app.py
```

## API Keys

To use the models, you'll need to set the appropriate API keys:

```bash
export GEMINI_API_KEY="your-gemini-key"
```

## Dataset

Download the C-MAPSS dataset and place the `*.txt` files in the `data/` directory.

## Optional: Telemetry Pipeline

Decoupled ingestion flow: App → RabbitMQ → consumer.py → InfluxDB.

To use RabbitMQ and InfluxDB:
1. Start infrastructure:
   ```bash
   docker compose up -d
   ```
2. Start the consumer in a separate terminal:
   ```bash
   source .venv/bin/activate
   python -m twin.consumer
   ```
3. Run the app with the pipeline enabled:
   ```bash
   export TWIN_ENABLE_PIPELINE=1
   streamlit run app.py
   ```
   (Alternatively, toggle "Enable RabbitMQ+Influx pipeline" in the sidebar.)

*Note: The consumer must be running for data to reach InfluxDB. If the consumer is down, the app publishes but data won't persist, and the dashboard will fall back to in-memory replay.*

## Credits
* Engine diagram by K. Aainsqatsi / Wikimedia Commons, ["Turbofan operation.svg"](https://commons.wikimedia.org/wiki/File:Turbofan_operation.svg), licensed CC BY 2.5.
