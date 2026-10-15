"""Sensor domain service orchestrating validation, timestamping, inference, and persistence."""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.schemas import SensorData, SensorReadingResponse
from services.prediction_service import prediction_service
from services.storage_service import storage_service

logger = logging.getLogger(__name__)


class SensorService:
    """Orchestrates ingestion of sensor telemetry, inference invocation, and storage."""

    def process_and_store_reading(
        self,
        sensor_data: SensorData,
        db: Session,
    ) -> SensorReadingResponse:
        """Process incoming sensor reading through prediction and database storage.

        Steps:
            1. Generate server-side ISO 8601 UTC timestamp.
            2. Request prediction from PredictionService.
            3. Persist record into SQLite via StorageService.
            4. Construct and return SensorReadingResponse.
        """
        # Server-side timestamp generation in ISO 8601 UTC format
        server_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

        logger.info(
            f"Received sensor data: temp={sensor_data.temperature}°C, "
            f"hum={sensor_data.humidity}%, mq135={sensor_data.mq135} at {server_timestamp}"
        )

        # Obtain prediction from ML abstraction
        prediction = prediction_service.predict_food_condition(
            temperature=sensor_data.temperature,
            humidity=sensor_data.humidity,
            mq135=sensor_data.mq135,
        )
        logger.info(f"Generated prediction: '{prediction}'")

        # Persist to database
        record = storage_service.save_reading(
            db=db,
            timestamp=server_timestamp,
            temperature=sensor_data.temperature,
            humidity=sensor_data.humidity,
            mq135=sensor_data.mq135,
            prediction=prediction,
        )

        # Return domain response object
        return SensorReadingResponse(
            id=record.id,
            timestamp=record.timestamp,
            temperature=record.temperature,
            humidity=record.humidity,
            mq135=record.mq135,
            prediction=record.prediction,
        )


sensor_service = SensorService()
