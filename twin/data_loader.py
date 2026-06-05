import pandas as pd
import numpy as np

# Column schema: 26 columns total
COLUMNS = (
    ["unit_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"] +
    [f"sensor_{i}" for i in range(1, 22)]
)

# Global caches for sensor lists
FLAT_SENSORS = []
ACTIVE_SENSORS = []

def load_raw(path: str = "data/train_FD001.txt") -> pd.DataFrame:
    """Loads raw CMAPSS data and assigns standard column names, dropping empty phantom columns."""
    df = pd.read_csv(path, sep=r"\s+", header=None)
    
    # Drop completely empty columns (often at the end due to trailing spaces)
    df = df.dropna(axis=1, how='all')
    
    # Assert we have exactly 26 columns left
    assert df.shape[1] == 26, f"Expected 26 columns, got {df.shape[1]}"
    
    df.columns = COLUMNS
    return df

def compute_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Computes Remaining Useful Life (RUL) per unit and adds it as a column."""
    # RUL = max(cycle within unit) - cycle
    max_cycles = df.groupby('unit_id')['cycle'].transform('max')
    df['RUL'] = max_cycles - df['cycle']
    return df

def find_flat_sensors(df: pd.DataFrame, threshold: float = 1e-6) -> list[str]:
    """Identifies sensor columns with zero or near-zero variance."""
    global FLAT_SENSORS, ACTIVE_SENSORS
    
    sensor_cols = [c for c in df.columns if c.startswith('sensor_')]
    flat = []
    active = []
    
    for col in sensor_cols:
        if df[col].std() <= threshold:
            flat.append(col)
        else:
            active.append(col)
            
    print(f"Identified flat sensors (std <= {threshold}): {flat}")
    
    FLAT_SENSORS = flat
    ACTIVE_SENSORS = active
    return flat

def drop_flat_sensors(df: pd.DataFrame, flat: list[str] = None) -> pd.DataFrame:
    """Drops the flat sensors from the dataframe."""
    if flat is None:
        flat = find_flat_sensors(df)
    return df.drop(columns=flat, errors='ignore')

def get_unit(unit_id: int = 1, path: str = "data/train_FD001.txt") -> pd.DataFrame:
    """Loads, computes RUL, drops flat sensors, and returns a single unit's trajectory."""
    df = load_raw(path)
    df = compute_rul(df)
    df = drop_flat_sensors(df)
    
    # Filter to the given unit
    unit_df = df[df['unit_id'] == unit_id].copy()
    
    # Sort and reset index
    unit_df = unit_df.sort_values(by='cycle', ascending=True).reset_index(drop=True)
    return unit_df

if __name__ == "__main__":
    import os
    import sys
    
    print("Running Smoke Test...")
    path = "data/train_FD001.txt"
    if not os.path.exists(path):
        print(f"FAIL: {path} not found. Cannot run smoke test.")
        sys.exit(1)
        
    df_raw = load_raw(path)
    num_units = df_raw['unit_id'].nunique()
    cycle_lengths = df_raw.groupby('unit_id')['cycle'].max()
    print(f"\nDataset Overview:")
    print(f"Total units: {num_units}")
    print(f"Cycle length range: {cycle_lengths.min()} - {cycle_lengths.max()}")
    
    unit_id = 1
    print(f"\nProcessing Unit {unit_id}...")
    unit_df = get_unit(unit_id, path)
    
    print(f"\nShape: {unit_df.shape}")
    print(f"Columns: {list(unit_df.columns)}")
    print(f"\nFirst 3 rows:\n{unit_df.head(3)}")
    print(f"\nLast 3 rows:\n{unit_df.tail(3)}")
    
    # Assertions
    assert unit_df['cycle'].is_monotonic_increasing, "FAIL: cycles are not sorted ascending"
    assert unit_df['RUL'].is_monotonic_decreasing, "FAIL: RUL is not monotonically decreasing"
    assert unit_df['RUL'].iloc[-1] == 0, "FAIL: Final RUL is not 0"
    
    flat_sensors = find_flat_sensors(df_raw)
    remaining_sensors = [c for c in unit_df.columns if c.startswith('sensor_')]
    for fs in flat_sensors:
        assert fs not in remaining_sensors, f"FAIL: Flat sensor {fs} was not dropped"
    
    print("\nSmoke test PASS")
