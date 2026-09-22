# Machine Learning Integration Guide

This directory (`backend/ml/`) is designated for the trained machine learning model artifacts produced by the ML team.

## Overview

The backend acts as the central inference coordinator. When an ESP32 sensor reading is received at `POST /api/sensor-data`, the backend routes the sensor telemetry to `services/prediction_service.py` to obtain an assessment of food condition before persisting the record to the SQLite database.

---

## Deliverable Artifacts

The ML team should place the finalized, trained model artifacts in this directory.

Recommended artifact options:
1. **Single Scikit-Learn Pipeline (Recommended)**:
   - File: `model.joblib` (or `pipeline.joblib`)
   - Encapsulates any feature scalers (e.g. `StandardScaler`, `MinMaxScaler`), transformers, and classifier (e.g. `RandomForestClassifier`, `SVC`, `XGBClassifier`) into a single `sklearn.pipeline.Pipeline`.
2. **Model + Scaler / Encoder**:
   - `model.joblib`
   - `scaler.joblib` (if preprocessing is external)
   - `label_encoder.joblib` (if numeric output requires class label mapping)

---

## Input Features & Order

The inference function `predict_food_condition` supplies a 2D array-like input to the model:

```python
features = [[temperature, humidity, mq135]]
```

| Feature Name | Type | Physical Units | Description | Expected Range |
|---|---|---|---|---|
| `temperature` | `float` | °C (Celsius) | Ambient storage temperature | -40.0 to 100.0 |
| `humidity` | `float` | % (Relative) | Ambient storage relative humidity | 0.0 to 100.0 |
| `mq135` | `float` | ADC / ppm | Gas sensor value (NH3, NOx, alcohol, benzene, smoke, CO2) | 0.0 to 10000.0 |

> **Note**: If your model was trained on scaled features, bundle the scaler inside an `sklearn.pipeline.Pipeline` when exporting to `model.joblib`. This ensures that calling `model.predict([[temp, hum, mq135]])` internally applies the scaling transformation.

---

## Model Export Example

In your ML training notebook/script, export your trained pipeline using `joblib`:

```python
import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Define pipeline
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])

# Fit pipeline on your training data (X has 3 columns: temperature, humidity, mq135)
pipeline.fit(X_train, y_train)

# Save pipeline artifact
joblib.dump(pipeline, "backend/ml/model.joblib")
```

---

## Activating Real ML Mode in Backend

By default, the backend runs in `ML_MODE=mock`. To switch to real ML model inference:

1. Copy your exported `model.joblib` into `backend/ml/model.joblib`.
2. Update the `.env` file (or set environment variables):
   ```ini
   ML_MODE=real
   MODEL_PATH=./ml/model.joblib
   ```
3. Restart the FastAPI server.
4. Verify status via `GET /api/health`:
   ```json
   {
     "backend": "online",
     "database": "online",
     "ml": "ready"
   }
   ```

---

## Lifecycle & Performance Rules

- **Startup Preloading**: The backend loads `model.joblib` into memory **once** during application startup (FastAPI lifespan). It is **never** reloaded from disk on per-request calls.
- **Resilience**: If `ML_MODE=real` is set but the model file is missing or corrupted, the backend will log an error, mark `ml` as `"unavailable"`, and gracefully fallback without crashing the server or interrupting sensor data ingestion.
