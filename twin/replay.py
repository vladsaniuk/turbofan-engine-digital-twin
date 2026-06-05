import pandas as pd
import numpy as np

def row_to_state(row: pd.Series) -> dict:
    """
    Converts a single DataFrame row to a clean twin-state dictionary.
    Casts numpy types to native Python types for JSON serialization.
    """
    state = {
        "unit_id": int(row["unit_id"]),
        "cycle": int(row["cycle"]),
        "RUL": int(row["RUL"]),
        "settings": {},
        "sensors": {}
    }
    
    for col, val in row.items():
        if col in ["unit_id", "cycle", "RUL"]:
            continue
            
        # Convert numpy numbers to python native types
        py_val = float(val) if isinstance(val, (np.floating, float)) else int(val) if isinstance(val, (np.integer, int)) else val
        
        if col.startswith("op_setting_"):
            state["settings"][col] = py_val
        elif col.startswith("sensor_"):
            state["sensors"][col] = py_val
            
    return state
