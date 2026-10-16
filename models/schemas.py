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
                "ml": "ready",
            }
        }
    }


class ActuatorState(BaseModel):
    """Current hardware actuation states representing ESP32 GPIOs and storage actuators."""

    alert_led: str = Field(..., description="LED status: 'GREEN', 'AMBER', or 'RED_PULSING'", examples=["GREEN"])
    buzzer: bool = Field(..., description="Acoustic buzzer alarm trigger (Active-LOW GPIO 12)", examples=[False])
    ventilation_fan: bool = Field(..., description="Chamber exhaust fan relay trigger for VOC purging", examples=[False])
    cooling_unit: bool = Field(..., description="Chamber cooling/refrigeration compressor trigger", examples=[False])


class DetailedPredictionResponse(BaseModel):
    """Comprehensive ML inference and storage diagnostics response."""

    prediction: str = Field(..., description="Condition assessment ('Fresh', 'Warning', 'Spoiled')", examples=["Fresh"])
    stage: str = Field(..., description="Ripening stage ('EARLY', 'TRANSITION', 'LATE')", examples=["EARLY"])
    probability_spoiled: float = Field(..., description="Continuous P(Spoiled) probability [0.0 .. 1.0]", examples=[0.0003])
    confidence_score: float = Field(..., description="Inference confidence percentage [50.0 .. 100.0]", examples=[99.9])
    mq135_adc: float = Field(..., description="MQ135 12-bit ADC reading [0..4095]", examples=[495.0])
    temperature: float = Field(..., description="Ambient temperature (°C)", examples=[14.2])
    humidity: float = Field(..., description="Relative humidity (%)", examples=[86.5])
    threshold: float = Field(..., description="Calibrated decision threshold ADC boundary", examples=[738.0])
    model_name: str = Field(..., description="Loaded Edge-AI model architecture", examples=["Edge-AI Stacking Hybrid"])
    status: str = Field(..., description="ML subsystem status ('ready', 'mock', 'unavailable')", examples=["ready"])
    actuators: ActuatorState
    storage_assessment: dict = Field(..., description="Produce shelf-life and environmental diagnostics")


class DatasetDayInfo(BaseModel):
    """Metadata for real experiment benchmark day datasets."""

    day_id: str = Field(..., examples=["D1"])
    filename: str = Field(..., examples=["Banana D1.csv"])
    label: str = Field(..., examples=["FRESH"])
    role: str = Field(..., examples=["benchmark"])
    sample_count: int = Field(..., examples=[27708])
    mean_mq135: float = Field(..., examples=[494.5])
    description: str = Field(..., examples=["Day 1: Baseline peak freshness"])


class DatasetSampleResponse(BaseModel):
    """Sample records from real banana dataset for testing harness."""

    day_id: str
    class_label: str
    samples: list[dict]

