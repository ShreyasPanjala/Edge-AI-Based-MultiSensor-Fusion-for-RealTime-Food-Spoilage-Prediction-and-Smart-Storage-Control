"""Tests for prediction service abstraction and GET /api/prediction endpoint."""

import pytest
from services.prediction_service import PredictionService, predict_food_condition


def test_mock_prediction_logic():
    """Verify that mock prediction returns predictable labels without error."""
    # Baseline condition
    pred_fresh = predict_food_condition(temperature=20.0, humidity=50.0, mq135=300.0)
    assert pred_fresh == "Fresh"

    # Warning condition
    pred_warning = predict_food_condition(temperature=31.0, humidity=60.0, mq135=700.0)
    assert pred_warning in ["Warning", "Spoiled"]

    # Spoiled condition
    pred_spoiled = predict_food_condition(temperature=35.0, humidity=85.0, mq135=1500.0)
    assert pred_spoiled == "Spoiled"


def test_prediction_endpoint_empty(client):
    """GET /api/prediction should return 404 when no readings exist."""
    response = client.get("/api/prediction")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_prediction_endpoint_with_reading(client):
    """GET /api/prediction should return the most recent prediction."""
    client.post(
        "/api/sensor-data",
        json={"temperature": 25.0, "humidity": 60.0, "mq135": 400.0},
    )
    response = client.get("/api/prediction")
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "timestamp" in data
    assert data["prediction"] == "Fresh"


def test_ml_service_real_mode_missing_file():
    """When ML_MODE is 'real' but model file is missing, status is 'unavailable'."""
    service = PredictionService()
    service.mode = "real"
    service.model_path = "./ml/non_existent_model.joblib"
    service.load_model()

    assert service.get_status() == "unavailable"
    # Fallback prediction should still succeed safely without raising exception
    result = service.predict_food_condition(25.0, 50.0, 400.0)
    assert isinstance(result, str)
