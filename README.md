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
