import os
import json
import numpy as np
import pandas as pd
from twin.data_loader import label_for

SYSTEM_PROMPT = """You are the digital twin of a turbofan engine (operating on simulated C-MAPSS FD001 run-to-failure telemetry). 
Your job is to reason over the provided telemetry to answer health, trend, what-if, and remaining useful life (RUL) questions.
Instructions:
- Ground every claim in the provided numbers.
- Cite specific sensors and cycles when explaining your reasoning.
- Be honest about uncertainty (you only see a limited window of history).
- Keep answers concise, direct, and limited to a few sentences."""

def round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 3)
    elif isinstance(obj, dict):
        return {k: round_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_floats(x) for x in obj]
    return obj

def state_to_prompt(state: dict, history_df: pd.DataFrame, window: int = 10) -> str:
    recent_history_df = history_df.tail(window)
    active_sensors = list(state["sensors"].keys())
    
    recent_history = []
    for _, row in recent_history_df.iterrows():
        cycle_data = {"cycle": int(row["cycle"])}
        for s in active_sensors:
            if s in row:
                cycle_data[s] = float(row[s])
        recent_history.append(cycle_data)
        
    deltas = {}
    if len(recent_history_df) > 1:
        oldest_row = recent_history_df.iloc[0]
        current_row = recent_history_df.iloc[-1]
        for s in active_sensors:
            if s in oldest_row and s in current_row:
                deltas[s] = float(current_row[s] - oldest_row[s])
    
    payload = {
        "unit_id": state["unit_id"],
        "current_cycle": state["cycle"],
        "current_RUL_ground_truth": state["RUL"],
        "current_settings": state["settings"],
        "current_sensors": {label_for(k): v for k, v in state["sensors"].items()},
        f"deltas_over_last_{len(recent_history_df)}_cycles": {label_for(k): v for k, v in deltas.items()},
        "recent_history": [
            {
                (label_for(k) if k != "cycle" else k): v 
                for k, v in row_data.items()
            } 
            for row_data in recent_history
        ]
    }
    
    compact_json = json.dumps(round_floats(payload), separators=(',', ':'))
    return f"Current Twin State & History:\n{compact_json}"

def ask_twin(question: str, state: dict, history_df: pd.DataFrame, window: int = 10) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Please set the GEMINI_API_KEY environment variable to use the LLM."
        
    user_content = state_to_prompt(state, history_df, window) + f"\n\nQuestion: {question}"
    
    try:
        from google import genai
        client = genai.Client()
        
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            contents=user_content,
        )
        return resp.text
    except Exception as e:
        return f"Error communicating with Gemini: {str(e)}"
