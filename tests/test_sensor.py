"""Tests for sensor data validation and ingestion endpoint POST /api/sensor-data."""

import pytest
from datetime import datetime


def test_ingest_valid_sensor_data(client):
    """Test successful ingestion of valid sensor telemetry."""
    payload = {
        "temperature": 28.5,
        "humidity": 67.2,
        "mq135": 742.0,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["id"] > 0
    assert data["temperature"] == 28.5
    assert data["humidity"] == 67.2
    assert data["mq135"] == 742.0
    assert "prediction" in data
    assert isinstance(data["prediction"], str)
    assert len(data["prediction"]) > 0

    # Verify server-generated ISO 8601 timestamp
    assert "timestamp" in data
    parsed_dt = datetime.fromisoformat(data["timestamp"])
    assert parsed_dt is not None


def test_missing_temperature_field(client):
    """Test validation rejection when temperature is omitted."""
    payload = {
        "humidity": 67.2,
        "mq135": 742.0,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 422


def test_missing_humidity_field(client):
    """Test validation rejection when humidity is omitted."""
    payload = {
        "temperature": 28.5,
        "mq135": 742.0,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 422


def test_missing_mq135_field(client):
    """Test validation rejection when mq135 is omitted."""
    payload = {
        "temperature": 28.5,
        "humidity": 67.2,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 422


def test_non_numeric_values(client):
    """Test validation rejection when non-numeric types are passed."""
    payload = {
        "temperature": "hot",
        "humidity": 67.2,
        "mq135": 742.0,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 422


def test_null_values(client):
    """Test validation rejection when values are null."""
    payload = {
        "temperature": None,
        "humidity": 67.2,
        "mq135": 742.0,
    }
    response = client.post("/api/sensor-data", json=payload)
    assert response.status_code == 422


def test_out_of_bounds_temperature(client):
    """Test rejection of physically impossible temperatures."""
    # Exceeds maximum 100°C
    response = client.post(
        "/api/sensor-data",
        json={"temperature": 150.0, "humidity": 50.0, "mq135": 500.0},
    )
    assert response.status_code == 422

    # Below minimum -40°C
    response = client.post(
        "/api/sensor-data",
        json={"temperature": -60.0, "humidity": 50.0, "mq135": 500.0},
    )
    assert response.status_code == 422


def test_out_of_bounds_humidity(client):
    """Test rejection of impossible relative humidity percentages."""
    # Negative humidity
    response = client.post(
        "/api/sensor-data",
        json={"temperature": 25.0, "humidity": -5.0, "mq135": 500.0},
    )
    assert response.status_code == 422

    # Exceeds 100%
    response = client.post(
        "/api/sensor-data",
        json={"temperature": 25.0, "humidity": 105.0, "mq135": 500.0},
    )
    assert response.status_code == 422


def test_out_of_bounds_mq135(client):
    """Test rejection of negative MQ135 sensor readings."""
    response = client.post(
        "/api/sensor-data",
        json={"temperature": 25.0, "humidity": 50.0, "mq135": -10.0},
    )
    assert response.status_code == 422


def test_invalid_json_payload(client):
    """Test rejection of malformed JSON."""
    response = client.post(
        "/api/sensor-data",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
