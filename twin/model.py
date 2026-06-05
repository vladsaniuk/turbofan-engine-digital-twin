import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from twin.data_loader import load_raw, compute_rul, drop_flat_sensors

MODEL_PATH = "models/rul_model.joblib"

def prepare_features(df):
    """Extract features (op_settings + active sensors)."""
    feature_cols = [c for c in df.columns if c.startswith('op_setting_') or c.startswith('sensor_')]
    return df[feature_cols]

def train_model(path="data/train_FD001.txt"):
    print("Loading data for training...")
    df = load_raw(path)
    df = compute_rul(df)
    df = drop_flat_sensors(df)
    
    # Cap RUL at 130
    df['RUL_clipped'] = df['RUL'].clip(upper=130)
    
    X = prepare_features(df)
    y = df['RUL_clipped']
    
    print(f"Training RandomForestRegressor on {len(X)} samples...")
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return model

def load_or_train(path="data/train_FD001.txt"):
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_model(path)

def predict_rul(model, state_or_df):
    """Predicts RUL from a twin state dict or a history DataFrame."""
    if isinstance(state_or_df, dict):
        # Extract features in the right order
        features = {}
        for k, v in state_or_df.get('settings', {}).items():
            features[k] = [v]
        for k, v in state_or_df.get('sensors', {}).items():
            features[k] = [v]
        # Make a single-row DataFrame (since feature names match the training data)
        X = pd.DataFrame(features)
        # Ensure correct column order by matching the training data (all op_settings then sensors)
        # We rely on pd.DataFrame sorting or just trusting the dict insertion order if it matches
        # Let's explicitly sort keys like prepare_features does:
        cols = [c for c in X.columns if c.startswith('op_setting_')] + [c for c in X.columns if c.startswith('sensor_')]
        X = X[cols]
        return model.predict(X)[0]
    elif isinstance(state_or_df, pd.DataFrame):
        X = prepare_features(state_or_df)
        return model.predict(X)

if __name__ == "__main__":
    print("Running Smoke Test for RUL Model...")
    df = load_raw("data/train_FD001.txt")
    df = compute_rul(df)
    df = drop_flat_sensors(df)
    
    # Split by unit: 1-80 train, 81-100 test
    train_df = df[df['unit_id'] <= 80].copy()
    test_df = df[df['unit_id'] > 80].copy()
    
    train_df['RUL_clipped'] = train_df['RUL'].clip(upper=130)
    test_df['RUL_clipped'] = test_df['RUL'].clip(upper=130)
    
    X_train = prepare_features(train_df)
    y_train = train_df['RUL_clipped']
    
    X_test = prepare_features(test_df)
    y_test = test_df['RUL_clipped'] # Evaluate on clipped or raw? MAE is usually reported on true RUL, but predictions are capped.
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Test MAE on Units 81-100: {mae:.2f}")
