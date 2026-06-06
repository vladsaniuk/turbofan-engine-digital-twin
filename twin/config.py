import os
import streamlit as st

def pipeline_active() -> bool:
    """Return True if the telemetry pipeline is active."""
    # Check session state first
    if "pipeline_enabled" in st.session_state:
        return st.session_state.pipeline_enabled
    
    # Fallback to env default
    env_val = os.environ.get("TWIN_ENABLE_PIPELINE", "0")
    return env_val.lower() in ("1", "true", "yes")
