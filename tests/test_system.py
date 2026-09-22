"""Tests for system health and telemetry retrieval endpoints."""

import pytest


def test_system_health(client):
    """GET /api/health should report status of backend, database, and ML service."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "online"
    assert data["database"] == "online"
    assert data["ml"] in ["mock", "ready", "unavailable"]


def test_latest_reading_empty(client):
    """GET /api/latest should return 404 when no data is recorded."""
    response = client.get("/api/latest")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_latest_reading_populated(client):
    """GET /api/latest should return the most recent reading after insertions."""
    # Post first reading
    client.post(
        "/api/sensor-data",
        json={"temperature": 22.0, "humidity": 55.0, "mq135": 350.0},
    )
    # Post second reading
    client.post(
        "/api/sensor-data",
        json={"temperature": 28.7, "humidity": 67.5, "mq135": 755.0},
    )

    response = client.get("/api/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == 28.7
    assert data["humidity"] == 67.5
    assert data["mq135"] == 755.0


def test_history_empty(client):
    """GET /api/history should return an empty list when no data is recorded."""
    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_history_ordering_and_limit(client):
    """GET /api/history should return records ordered newest first and respect limits."""
    # Post 3 readings
    for i in range(1, 4):
        client.post(
            "/api/sensor-data",
            json={"temperature": 20.0 + i, "humidity": 50.0 + i, "mq135": 300.0 + i},
        )

    # Fetch with default limit
    response = client.get("/api/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 3
    # Check newest-first ordering (id 3 should be first)
    assert history[0]["id"] == 3
    assert history[1]["id"] == 2
    assert history[2]["id"] == 1

    # Fetch with custom limit=2
    response_limited = client.get("/api/history?limit=2")
    assert response_limited.status_code == 200
    limited_history = response_limited.json()
    assert len(limited_history) == 2
    assert limited_history[0]["id"] == 3
    assert limited_history[1]["id"] == 2


def test_history_invalid_limit(client):
    """GET /api/history with limit=0 or limit>1000 should return validation error 422."""
    res_zero = client.get("/api/history?limit=0")
    assert res_zero.status_code == 422

    res_large = client.get("/api/history?limit=1001")
    assert res_large.status_code == 422


def test_root_redirect(client):
    """GET / should redirect to /docs."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [307, 302]
    assert response.headers["location"] == "/docs"
