"""SQLAlchemy ORM models for persistent storage."""

from sqlalchemy import Column, Integer, Float, String, DateTime
from database.database import Base


class SensorReadingDB(Base):
    """Database table representing sensor readings and spoilage predictions."""

    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(String, index=True, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    mq135 = Column(Float, nullable=False)
    prediction = Column(String, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<SensorReadingDB(id={self.id}, timestamp='{self.timestamp}', "
            f"temp={self.temperature}, hum={self.humidity}, mq135={self.mq135}, "
            f"prediction='{self.prediction}')>"
        )
