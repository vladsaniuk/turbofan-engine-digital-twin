import json
import math

SENSOR_DTDL_MAP = {
    "sensor_2": "LPC_outlet_temp",
    "sensor_3": "HPC_outlet_temp",
    "sensor_4": "LPT_outlet_temp",
    "sensor_6": "bypass_duct_total_pressure",
    "sensor_7": "HPC_outlet_pressure",
    "sensor_8": "fan_speed",
    "sensor_9": "core_speed",
    "sensor_11": "HPC_outlet_static_pressure",
    "sensor_12": "fuel_flow_ratio",
    "sensor_13": "corrected_fan_speed",
    "sensor_14": "corrected_core_speed",
    "sensor_15": "bypass_ratio",
    "sensor_17": "bleed_enthalpy",
    "sensor_20": "HPT_coolant_bleed_flow",
    "sensor_21": "LPT_coolant_bleed_flow"
}

def load_contract(path="models/engine.dtdl.json"):
    with open(path, "r") as f:
        return json.load(f)

def validate_row(state: dict, path="models/engine.dtdl.json") -> tuple[bool, list[str]]:
    contract = load_contract(path)
    contents = contract.get("contents", [])
    
    # Build list of required fields from DTDL
    required_telemetry = []
    required_properties = []
    
    for item in contents:
        if item.get("@type") == "Telemetry":
            required_telemetry.append(item["name"])
        elif item.get("@type") == "Property":
            required_properties.append(item["name"])
            
    violations = []
    
    # Check properties
    for prop in required_properties:
        if prop not in state:
            violations.append(f"Missing property: {prop}")
        elif not math.isfinite(state[prop]):
            violations.append(f"Property {prop} is not finite")
            
    # Check telemetry (RUL + op_settings + sensors)
    flat_state = {}
    if "RUL" in state:
        flat_state["RUL"] = state["RUL"]
    for k, v in state.get("settings", {}).items():
        flat_state[k] = v
    for k, v in state.get("sensors", {}).items():
        # state["sensors"] has either friendly names or raw sensor_N. 
        # But wait, app.py passes `current_state` which has raw `sensor_N` as keys!
        # Because we only relabelled it for display `display_state`.
        if k in SENSOR_DTDL_MAP:
            flat_state[SENSOR_DTDL_MAP[k]] = v
        else:
            flat_state[k] = v

    for tel in required_telemetry:
        if tel not in flat_state:
            violations.append(f"Missing telemetry: {tel}")
        elif not math.isfinite(flat_state[tel]):
            violations.append(f"Telemetry {tel} is not finite")
            
    return len(violations) == 0, violations
