"""Sensor data ingestion API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from models.schemas import SensorData, SensorReadingResponse
from services.sensor_service import sensor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Sensor Data"])


@router.post(
    "/sensor-data",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Sensor Telemetry",
    description=(
        "Receive real-time multi-sensor telemetry (temperature, humidity, MQ135) from an ESP32 "
        "or client simulation. Generates a server-side UTC timestamp, queries the ML prediction "
        "engine, persists the reading to SQLite, and returns the complete record."
    ),
    responses={
        201: {
            "description": "Sensor reading successfully validated, predicted, and persisted.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "timestamp": "2026-09-22T14:30:20Z",
                        "temperature": 28.5,
                        "humidity": 67.2,
                        "mq135": 742.0,
                        "prediction": "Fresh",
                    }
                }
            },
        },
        422: {
            "description": "Validation Error: Missing fields, invalid JSON, non-numeric values, or out-of-range sensor readings.",
        },
        500: {
            "description": "Internal Server Error: Database failure during storage.",
        },
    },
)
def ingest_sensor_data(
    data: SensorData,
    db: Session = Depends(get_db),
) -> SensorReadingResponse:
    """Validate, evaluate, and persist incoming sensor data."""
    try:
        return sensor_service.process_and_store_reading(data, db)
    except Exception as exc:
        logger.error(f"Failed to process and store sensor reading: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist sensor reading due to an internal server error.",
        )
