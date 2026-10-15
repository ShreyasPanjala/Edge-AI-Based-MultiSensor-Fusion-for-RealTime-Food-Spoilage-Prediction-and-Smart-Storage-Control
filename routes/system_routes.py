"""System and telemetry retrieval routes: health checks, latest data, and history."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database.database import get_db
from models.schemas import SensorReadingResponse, HealthResponse
from services.storage_service import storage_service
from services.prediction_service import prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["System & Telemetry"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Component Status",
    description=(
        "Returns the operational status of the FastAPI backend, the SQLite database connectivity, "
        "and the ML inference integration ('mock', 'ready', or 'unavailable')."
    ),
    responses={
        200: {
            "description": "Health status retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "backend": "online",
                        "database": "online",
                        "ml": "mock",
                    }
                }
            },
        }
    },
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
    responses={
        200: {
            "description": "Most recent reading retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 15,
                        "timestamp": "2026-09-22T14:35:10Z",
                        "temperature": 28.7,
                        "humidity": 67.5,
                        "mq135": 755.0,
                        "prediction": "Fresh",
                    }
                }
            },
        },
        404: {
            "description": "No readings found in the database.",
            "content": {
                "application/json": {
                    "example": {"detail": "No sensor readings recorded yet."}
                }
            },
        },
    },
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
    description=(
        "Retrieve a chronologically ordered (newest first) list of historical sensor readings "
        "and predictions, with an optional limit parameter."
    ),
    responses={
        200: {
            "description": "List of historical sensor records retrieved successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 2,
                            "timestamp": "2026-09-22T14:35:10Z",
                            "temperature": 28.7,
                            "humidity": 67.5,
                            "mq135": 755.0,
                            "prediction": "Fresh",
                        },
                        {
                            "id": 1,
                            "timestamp": "2026-09-22T14:30:20Z",
                            "temperature": 28.5,
                            "humidity": 67.2,
                            "mq135": 742.0,
                            "prediction": "Fresh",
                        },
                    ]
                }
            },
        }
    },
)
def get_reading_history(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of historical records to return (1 - 1000)",
    ),
    db: Session = Depends(get_db),
) -> List[SensorReadingResponse]:
    """Fetch historical records bounded by limit."""
    records = storage_service.get_history(db, limit=limit)
    return [SensorReadingResponse.model_validate(r) for r in records]
