import networkx as nx
import numpy as np
import pandas as pd

SENSOR_SUBSYSTEM = {
    "sensor_2":  "LPC",   # LPC outlet temp
    "sensor_3":  "HPC",   # HPC outlet temp
    "sensor_4":  "LPT",   # LPT outlet temp
    "sensor_6":  "Fan",   # bypass duct pressure
    "sensor_7":  "HPC",   # HPC outlet pressure
    "sensor_8":  "Fan",   # fan speed
    "sensor_9":  "HPC",   # core speed
    "sensor_11": "HPC",   # HPC static pressure
    "sensor_12": "Combustor",  # fuel/pressure ratio
    "sensor_13": "Fan",   # corrected fan speed
    "sensor_14": "HPC",   # corrected core speed
    "sensor_15": "Fan",   # bypass ratio
    "sensor_17": "HPT",   # bleed enthalpy
    "sensor_20": "HPT",   # HPT coolant bleed
    "sensor_21": "LPT",   # LPT coolant bleed
}

def build_graph(unit_id: int) -> nx.DiGraph:
    """Build Fleet -> Engine -> Subsystem -> Sensor graph."""
    G = nx.DiGraph()
    
    fleet_node = "Fleet"
    engine_node = f"Engine_{unit_id}"
    
    G.add_node(fleet_node, type="Fleet")
    G.add_node(engine_node, type="Engine")
    G.add_edge(fleet_node, engine_node, rel="rel_has_engine")
    
    subsystems = set(SENSOR_SUBSYSTEM.values())
    for sub in subsystems:
        sub_node = f"{engine_node}_{sub}"
        G.add_node(sub_node, type="Subsystem", name=sub)
        G.add_edge(engine_node, sub_node, rel="rel_has_subsystem")
        
    for sensor, sub in SENSOR_SUBSYSTEM.items():
        sub_node = f"{engine_node}_{sub}"
        sensor_node = f"{engine_node}_{sensor}"
        G.add_node(sensor_node, type="Sensor", name=sensor)
        G.add_edge(sub_node, sensor_node, rel="rel_has_sensor")
        
    return G

def subsystem_health(state: dict, history_df: pd.DataFrame, window: int = 20) -> dict:
    """Compute degradation score for each subsystem."""
    active_sensors = [s for s in state["sensors"].keys() if s in SENSOR_SUBSYSTEM]
    
    recent_history = history_df.tail(window)
    if len(recent_history) < 2:
        return {sub: 0.0 for sub in set(SENSOR_SUBSYSTEM.values())}
        
    oldest_row = recent_history.iloc[0]
    current_row = recent_history.iloc[-1]
    
    scores = {}
    for sensor in active_sensors:
        sub = SENSOR_SUBSYSTEM[sensor]
        if sensor in oldest_row and sensor in current_row:
            old_val = float(oldest_row[sensor])
            cur_val = float(current_row[sensor])
            
            # Use percent change (or 0 if old_val is 0)
            if old_val != 0:
                drift = abs(cur_val - old_val) / abs(old_val)
            else:
                drift = abs(cur_val - old_val)
                
            if sub not in scores:
                scores[sub] = []
            scores[sub].append(drift)
            
    # Aggregate by subsystem
    result = {}
    for sub in set(SENSOR_SUBSYSTEM.values()):
        if sub in scores and len(scores[sub]) > 0:
            result[sub] = float(np.mean(scores[sub]))
        else:
            result[sub] = 0.0
            
    return result
