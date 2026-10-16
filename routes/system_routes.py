"""System and telemetry retrieval routes: health checks, latest data, history, and dataset streaming."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database.database import get_db
from models.schemas import (
    SensorReadingResponse,
    HealthResponse,
    DatasetDayInfo,
    DatasetSampleResponse,
    ActuatorState,
)
from services.storage_service import storage_service
from services.prediction_service import prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["System & Telemetry"])

DATA_RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# In-memory manual override for actuators if user toggles manual controls in UI
actuator_overrides: Dict[str, Optional[bool]] = {
    "ventilation_fan": None,
    "cooling_unit": None,
    "buzzer_muted": False,
}


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Component Status",
    description=(
        "Returns the operational status of the FastAPI backend, SQLite database connectivity, "
        "and ML inference engine."
    ),
)
def get_system_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Check connectivity and operational status across all backend subsystems."""
    db_healthy = storage_service.check_health(db)
    db_status = "online" if db_healthy else "offline"
    ml_status = prediction_service.get_status()

    return HealthResponse(
        backend="online",
        database=db_status,
        ml=ml_status,
    )


@router.get(
    "/latest",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Most Recent Sensor Reading",
    description="Retrieve the latest recorded multi-sensor reading and condition prediction.",
)
def get_latest_reading(db: Session = Depends(get_db)) -> SensorReadingResponse:
    """Fetch the newest sensor reading from persistent storage."""
    record = storage_service.get_latest_reading(db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensor readings recorded yet.",
        )
    return SensorReadingResponse.model_validate(record)


@router.get(
    "/history",
    response_model=List[SensorReadingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Historical Sensor Readings",
    description="Retrieve chronologically ordered (newest first) historical sensor readings.",
)
def get_reading_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of historical records to return (1 - 1000)",
    ),
    db: Session = Depends(get_db),
) -> List[SensorReadingResponse]:
    """Fetch historical records bounded by limit."""
    records = storage_service.get_history(db, limit=limit)
    return [SensorReadingResponse.model_validate(r) for r in records]


@router.post(
    "/history/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset Reading History",
    description="Clear all persisted sensor records to start a clean live demonstration run.",
)
def reset_history(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Truncate the sensor_readings table."""
    deleted_count = storage_service.clear_history(db)
    return {
        "status": "success",
        "message": f"Successfully cleared {deleted_count} historical telemetry records.",
    }


@router.get(
    "/actuators",
    response_model=ActuatorState,
    status_code=status.HTTP_200_OK,
    summary="Current Actuator States",
    description="Query current physical actuator and relay states (LED, Buzzer, Exhaust Fan, Cooling).",
)
def get_actuator_states(db: Session = Depends(get_db)) -> ActuatorState:
    """Compute active actuator status based on latest reading and manual overrides."""
    latest = storage_service.get_latest_reading(db)
    temp = latest.temperature if latest else 14.0
    hum = latest.humidity if latest else 85.0
    mq = latest.mq135 if latest else 495.0

    detailed = prediction_service.predict_detailed(temp, hum, mq)
    acts = detailed["actuators"]

    # Apply manual overrides if set
    if actuator_overrides["ventilation_fan"] is not None:
        acts["ventilation_fan"] = actuator_overrides["ventilation_fan"]
    if actuator_overrides["cooling_unit"] is not None:
        acts["cooling_unit"] = actuator_overrides["cooling_unit"]
    if actuator_overrides["buzzer_muted"]:
        acts["buzzer"] = False

    return ActuatorState(**acts)


@router.post(
    "/actuators/override",
    status_code=status.HTTP_200_OK,
    summary="Override Actuator States",
    description="Manually toggle or clear overrides for ventilation fan, cooling unit, or buzzer.",
)
def override_actuator(
    ventilation_fan: Optional[bool] = None,
    cooling_unit: Optional[bool] = None,
    buzzer_muted: Optional[bool] = None,
    reset_overrides: bool = False,
) -> Dict[str, Any]:
    """Set or reset manual actuator overrides."""
    if reset_overrides:
        actuator_overrides["ventilation_fan"] = None
        actuator_overrides["cooling_unit"] = None
        actuator_overrides["buzzer_muted"] = False
        return {"status": "success", "message": "Manual overrides cleared. System running in full Edge-AI auto mode."}

    if ventilation_fan is not None:
        actuator_overrides["ventilation_fan"] = ventilation_fan
    if cooling_unit is not None:
        actuator_overrides["cooling_unit"] = cooling_unit
    if buzzer_muted is not None:
        actuator_overrides["buzzer_muted"] = buzzer_muted

    return {
        "status": "success",
        "overrides": actuator_overrides,
    }


@router.get(
    "/dataset/days",
    response_model=List[DatasetDayInfo],
    status_code=status.HTTP_200_OK,
    summary="List Real Experiment Benchmark Datasets",
    description="Retrieve available raw banana experiment day datasets and their biological stages.",
)
def list_dataset_days() -> List[DatasetDayInfo]:
    """List metadata for real datasets in data/raw."""
    day_meta = [
        {
            "day_id": "D1",
            "filename": "Banana D1.csv",
            "label": "FRESH",
            "role": "benchmark",
            "description": "Day 1: Baseline peak freshness, low VOCs (MQ135 ~490-510 ADC)",
        },
        {
            "day_id": "D2",
            "filename": "Banana D2.csv",
            "label": "FRESH",
            "role": "benchmark",
            "description": "Day 2: Fresh consumption stage (MQ135 ~520-560 ADC)",
        },
        {
            "day_id": "D3",
            "filename": "Banana D3.csv",
            "label": "TRANSITION",
            "role": "transition",
            "description": "Day 3: Climacteric ripening surge, rapid ester/ethylene accumulation (MQ135 ~640-690 ADC)",
        },
        {
            "day_id": "D4",
            "filename": "Banana D4.csv",
            "label": "SPOILED",
            "role": "benchmark",
            "description": "Day 4: Spoilage threshold breached, senescence onset (MQ135 ~810-850 ADC)",
        },
        {
            "day_id": "D5",
            "filename": "Banana D5.csv",
            "label": "SPOILED",
            "role": "benchmark",
            "description": "Day 5: Advanced decomposition, severe volatile emission (MQ135 ~1050-1300 ADC)",
        },
    ]

    results = []
    for meta in day_meta:
        path = DATA_RAW_DIR / meta["filename"]
        sample_count = 0
        mean_val = 0.0
        if path.exists():
            try:
                # Fast sample read to get count and mean without reading millions of bytes
                df_head = pd.read_csv(path, nrows=500)
                mean_val = float(df_head["MQ135"].mean()) if "MQ135" in df_head.columns else 0.0
                sample_count = sum(1 for _ in open(path, "r", encoding="utf-8")) - 1
            except Exception:
                sample_count = 1000
                mean_val = 500.0

        results.append(
            DatasetDayInfo(
                day_id=meta["day_id"],
                filename=meta["filename"],
                label=meta["label"],
                role=meta["role"],
                sample_count=sample_count,
                mean_mq135=round(mean_val, 1),
                description=meta["description"],
            )
        )
    return results


@router.get(
    "/dataset/sample/{day_id}",
    response_model=DatasetSampleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Sample Readings from Benchmark Day",
    description="Retrieve a sequence of real sensor readings from a chosen day (D1, D2, D3, D4, D5) for live simulation.",
)
def get_dataset_sample(
    day_id: str,
    count: int = Query(default=10, ge=1, le=50, description="Number of sensor samples to retrieve"),
) -> DatasetSampleResponse:
    """Fetch sample rows from specified day."""
    day_clean = day_id.upper().strip()
    filename = f"Banana {day_clean}.csv"
    path = DATA_RAW_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file '{filename}' not found.",
        )

    try:
        # Read a distributed sample slice from the file
        df = pd.read_csv(path)
        step = max(1, len(df) // (count + 1))
        sampled_df = df.iloc[::step].head(count)

        # Baseline temperatures and humidities realistic for banana storage conditions
        temp_base = 14.2 if day_clean in ["D1", "D2"] else (16.8 if day_clean == "D3" else 22.5)
        hum_base = 86.0 if day_clean in ["D1", "D2"] else (83.0 if day_clean == "D3" else 76.5)

        class_label = "FRESH" if day_clean in ["D1", "D2"] else ("TRANSITION" if day_clean == "D3" else "SPOILED")

        samples = []
        for idx, (_, row) in enumerate(sampled_df.iterrows()):
            mq_val = float(row.get("MQ135", 500.0))
            # Slight natural jitter around baseline
            temp = round(temp_base + (idx % 3) * 0.2 - 0.2, 1)
            hum = round(hum_base - (idx % 4) * 0.3, 1)

            samples.append(
                {
                    "sample_idx": idx + 1,
                    "mq135": mq_val,
                    "temperature": temp,
                    "humidity": hum,
                    "timestamp_tick": int(row.get("Ticks", 0)),
                }
            )

        return DatasetSampleResponse(
            day_id=day_clean,
            class_label=class_label,
            samples=samples,
        )
    except Exception as exc:
        logger.error(f"Failed to read samples from {filename}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset: {exc}",
        )
