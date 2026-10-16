"""Storage service isolating database access logic for sensor readings."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from database.models import SensorReadingDB

logger = logging.getLogger(__name__)


class StorageService:
    """Encapsulates all persistence operations for sensor telemetry and predictions."""

    def save_reading(
        self,
        db: Session,
        timestamp: str,
        temperature: float,
        humidity: float,
        mq135: float,
        prediction: str,
    ) -> SensorReadingDB:
        """Persist a new sensor reading with its associated prediction to the database."""
        logger.debug(f"Persisting sensor reading at {timestamp} with prediction '{prediction}'")
        record = SensorReadingDB(
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            mq135=mq135,
            prediction=prediction,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Sensor reading successfully saved with ID: {record.id}")
        return record

    def get_latest_reading(self, db: Session) -> Optional[SensorReadingDB]:
        """Fetch the most recent sensor reading by ID descending."""
        return db.query(SensorReadingDB).order_by(desc(SensorReadingDB.id)).first()

    def get_history(self, db: Session, limit: int = 100) -> List[SensorReadingDB]:
        """Fetch historical sensor readings ordered newest-first, bounded by limit."""
        return (
            db.query(SensorReadingDB)
            .order_by(desc(SensorReadingDB.id))
            .limit(limit)
            .all()
        )

    def clear_history(self, db: Session) -> int:
        """Clear all historical sensor readings from database."""
        deleted = db.query(SensorReadingDB).delete()
        db.commit()
        logger.info(f"Cleared {deleted} records from sensor_readings table.")
        return deleted

    def check_health(self, db: Session) -> bool:
        """Perform a lightweight database health check ping."""
        try:
            db.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.error(f"Database health check failed: {exc}")
            return False


storage_service = StorageService()

