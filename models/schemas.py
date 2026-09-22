"""Pydantic data schemas and validation models for sensor data and API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SensorData(BaseModel):
    """Input schema for sensor telemetry received from ESP32 or test clients."""

    temperature: float = Field(
        ...,
        description="Ambient temperature in degrees Celsius (°C). Valid range: -40.0 to 100.0.",
        ge=-40.0,
        le=100.0,
        examples=[28.5],
    )
    humidity: float = Field(
        ...,
        description="Relative ambient humidity percentage (%). Valid range: 0.0 to 100.0.",
        ge=0.0,
        le=100.0,
        examples=[67.2],
    )
    mq135: float = Field(
        ...,
        description="MQ135 air quality / gas sensor reading (ADC value or ppm). Valid range: 0.0 to 10000.0.",
        ge=0.0,
        le=10000.0,
        examples=[742.0],
    )

    @field_validator("temperature", "humidity", "mq135", mode="before")
    @classmethod
    def validate_not_none(cls, value, info):
        """Ensure no null or None values are accepted for sensor readings."""
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "temperature": 28.5,
                "humidity": 67.2,
                "mq135": 742.0,
            }
        }
    }


class SensorReadingResponse(BaseModel):
    """Standard response model for a recorded sensor reading with its prediction."""

    id: int = Field(..., description="Unique database identifier for the record", examples=[1])
    timestamp: str = Field(
        ...,
        description="Server-generated ISO 8601 UTC timestamp of reading receipt",
        examples=["2026-09-22T14:30:20"],
    )
    temperature: float = Field(..., description="Recorded temperature in °C", examples=[28.5])
    humidity: float = Field(..., description="Recorded relative humidity %", examples=[67.2])
    mq135: float = Field(..., description="Recorded MQ135 sensor reading", examples=[742.0])
    prediction: str = Field(
        ...,
        description="Food condition assessment from the prediction service (e.g., 'Fresh', 'Spoiled')",
        examples=["Fresh"],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "timestamp": "2026-09-22T14:30:20",
                "temperature": 28.5,
                "humidity": 67.2,
                "mq135": 742.0,
                "prediction": "Fresh",
            }
        },
    }


class PredictionResponse(BaseModel):
    """Response model for the latest food condition prediction."""

    prediction: str = Field(
        ...,
        description="Current food spoilage assessment label",
        examples=["Fresh"],
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 UTC timestamp corresponding to the prediction",
        examples=["2026-09-22T14:35:10"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction": "Fresh",
                "timestamp": "2026-09-22T14:35:10",
            }
        }
    }


class HealthResponse(BaseModel):
    """Health status check response for monitoring subsystems."""

    backend: str = Field(..., description="FastAPI service health status", examples=["online"])
    database: str = Field(..., description="SQLite persistent storage connectivity", examples=["online"])
    ml: str = Field(..., description="ML inference module status: 'mock', 'ready', or 'unavailable'", examples=["mock"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "backend": "online",
                "database": "online",
                "ml": "mock",
            }
        }
    }
