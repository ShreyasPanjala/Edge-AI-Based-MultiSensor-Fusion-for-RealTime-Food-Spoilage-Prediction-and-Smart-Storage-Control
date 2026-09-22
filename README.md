# Smart Food Storage — Backend

> **Edge AI-Based Multi-Sensor Fusion System for Real-Time Food Spoilage Prediction and Smart Storage Control**

A high-performance, modular FastAPI backend responsible for receiving real-time multi-sensor telemetry, evaluating food spoilage conditions through an ML inference abstraction layer, persisting records in SQLite, and providing clean REST APIs for frontend monitoring dashboards and future smart storage actuators.

---

## 1. Project Purpose

Food preservation and spoilage detection require continuous environmental monitoring and multi-sensor fusion. This backend serves as the central communication and data processing hub:
- Receives temperature, humidity, and MQ135 air-quality telemetry from edge hardware (e.g. ESP32).
- Validates sensor readings against physical constraints and attaches server-generated ISO 8601 timestamps.
- Integrates with machine-learning inference pipelines (mock mode for isolated development, scikit-learn/joblib for production).
- Stores telemetry and spoilage predictions in a persistent SQLite database.
- Serves real-time state, history, and system health status to web dashboards and control actuators.

---

## 2. Backend Architecture

```
                       ┌─────────────────────────┐
                       │       ESP32 Node        │
                       │ (Temp, Hum, MQ135 Gas)  │
                       └────────────┬────────────┘
                                    │ HTTP POST /api/sensor-data
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                     FastAPI Backend                     │
       │                                                         │
       │  ┌───────────────────────┐   ┌───────────────────────┐  │
       │  │     Sensor Router     │   │   System / History    │  │
       │  └───────────┬───────────┘   └───────────▲───────────┘  │
       │              │                           │              │
       │  ┌───────────▼───────────┐               │              │
       │  │     Sensor Service    │               │              │
       │  └─────┬───────────────┬─┘               │              │
       │        │               │                 │              │
       │  ┌─────▼─────┐   ┌─────▼──────┐          │              │
       │  │Prediction │   │  Storage   │          │              │
       │  │  Service  │   │  Service   │          │              │
       │  └─────┬─────┘   └─────┬──────┘          │              │
       └────────┼───────────────┼─────────────────┼──────────────┘
                │               ▼                 │
     ┌──────────▼──────────┐ ┌────────────────────┴────────────┐
     │ ML Model Pipeline   │ │ SQLite Persistent Storage       │
     │ (Mock / Joblib)     │ │ (smart_food_storage.db)         │
     └─────────────────────┘ └─────────────────────────────────┘
                                       ▲
                                       │ HTTP GET (/latest, /history)
                       ┌───────────────┴─────────┐
                       │   Frontend Dashboard    │
                       │   (Web UI / Mobile)     │
                       └─────────────────────────┘
```

---

## 3. Project Structure

```
backend/
├── main.py                     # FastAPI application setup, lifespan, CORS, and router registration
├── requirements.txt            # Minimal production and testing dependencies
├── .env.example                # Template for environment variables
├── README.md                   # Complete backend documentation (this file)
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Pydantic Settings configuration loader
│
├── models/
│   ├── __init__.py
│   └── schemas.py              # Pydantic validation models and response schemas
│
├── database/
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy SQLite engine and session dependency
│   └── models.py               # SensorReadingDB ORM table mapping
│
├── services/
│   ├── __init__.py
│   ├── sensor_service.py       # Validation, timestamping, inference, and persistence orchestration
│   ├── storage_service.py      # Database query abstraction layer
│   └── prediction_service.py   # ML inference abstraction (mock & joblib model loading)
│
├── routes/
│   ├── __init__.py
│   ├── sensor_routes.py        # POST /api/sensor-data
│   ├── prediction_routes.py    # GET /api/prediction
│   └── system_routes.py        # GET /api/health, GET /api/latest, GET /api/history
│
├── ml/
│   └── README.md               # Contract and instructions for ML team
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures and in-memory test database setup
    ├── test_sensor.py          # Validation and ingestion tests
    ├── test_prediction.py      # Prediction service and mock unit tests
    └── test_system.py          # System health and query tests
```

---

## 4. Virtual Environment & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- `pip` package manager

### 1. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
# Inside backend directory
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Configuration

Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Key environment variables:

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `"Smart Food Storage Backend"` | Application identifier |
| `APP_HOST` | `0.0.0.0` | Host interface (0.0.0.0 allows LAN access) |
| `APP_PORT` | `8000` | HTTP port |
| `DEBUG` | `false` | Enable verbose logging |
| `DATABASE_URL` | `sqlite:///./smart_food_storage.db` | SQLite connection URI |
| `ML_MODE` | `mock` | Inference mode: `"mock"` or `"real"` |
| `MODEL_PATH` | `./ml/model.joblib` | Path to trained joblib pipeline |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed web origins |

---

## 6. Running the Server

Start the server using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 7. Sensor Data Format & Validation

The physical system uses an ESP32 equipped with:
1. **Temperature sensor** (°C)
2. **Humidity sensor** (% RH)
3. **MQ135 air-quality/gas sensor** (ADC value / ppm)

### Expected Payload
```json
{
  "temperature": 28.5,
  "humidity": 67.2,
  "mq135": 742.0
}
```

### Validation Constraints
- All three fields are strictly required. Missing fields return `422 Unprocessable Entity`.
- Non-numeric or null values are rejected with `422`.
- Physical boundary checks:
  - `temperature`: `-40.0` to `100.0` °C
  - `humidity`: `0.0` to `100.0` %
  - `mq135`: `0.0` to `10000.0`

---

## 8. API Endpoints

### 1. Ingest Sensor Telemetry
- **Method & Path**: `POST /api/sensor-data`
- **Status Code**: `201 Created`
- **Description**: Receives telemetry from ESP32, generates server UTC timestamp, runs ML inference, and saves to database.
- **Request Body**:
  ```json
  {
    "temperature": 28.5,
    "humidity": 67.2,
    "mq135": 742.0
  }
  ```
- **Response**:
  ```json
  {
    "id": 1,
    "timestamp": "2026-09-22T08:58:30Z",
    "temperature": 28.5,
    "humidity": 67.2,
    "mq135": 742.0,
    "prediction": "Fresh"
  }
  ```

### 2. Get Most Recent Reading
- **Method & Path**: `GET /api/latest`
- **Status Code**: `200 OK` (or `404 Not Found` if no data exists)
- **Response**:
  ```json
  {
    "id": 15,
    "timestamp": "2026-09-22T09:05:10Z",
    "temperature": 28.7,
    "humidity": 67.5,
    "mq135": 755.0,
    "prediction": "Fresh"
  }
  ```

### 3. Get Telemetry History
- **Method & Path**: `GET /api/history?limit=100`
- **Parameters**: `limit` (optional integer, 1 to 1000, default: 100)
- **Status Code**: `200 OK`
- **Response**:
  ```json
  [
    {
      "id": 2,
      "timestamp": "2026-09-22T09:05:10Z",
      "temperature": 28.7,
      "humidity": 67.5,
      "mq135": 755.0,
      "prediction": "Fresh"
    },
    {
      "id": 1,
      "timestamp": "2026-09-22T09:00:20Z",
      "temperature": 28.5,
      "humidity": 67.2,
      "mq135": 742.0,
      "prediction": "Fresh"
    }
  ]
  ```

### 4. Get Latest Prediction
- **Method & Path**: `GET /api/prediction`
- **Status Code**: `200 OK` (or `404 Not Found` if no readings recorded)
- **Response**:
  ```json
  {
    "prediction": "Fresh",
    "timestamp": "2026-09-22T09:05:10Z"
  }
  ```

### 5. Subsystem Health Check
- **Method & Path**: `GET /api/health`
- **Status Code**: `200 OK`
- **Response**:
  ```json
  {
    "backend": "online",
    "database": "online",
    "ml": "mock"
  }
  ```
  *(When real ML is loaded, `"ml"` reports `"ready"`. If model loading fails, reports `"unavailable"`).*

---

## 9. Machine Learning Integration

### Mock Mode (`ML_MODE=mock`)
Default development mode. Uses deterministic heuristic rules to return `"Fresh"`, `"Warning"`, or `"Spoiled"` based on test threshold values. Mock predictions are clearly reported via `GET /api/health` (`"ml": "mock"`).

### Real Model Mode (`ML_MODE=real`)
When the ML team provides a trained model:
1. Place the trained scikit-learn pipeline into `ml/model.joblib`.
2. Set `ML_MODE=real` in `.env`.
3. The model is loaded into memory **once at application startup** (via FastAPI lifespan) rather than per-request.
4. Input features passed to `model.predict`: `[[temperature, humidity, mq135]]`.
5. See [`ml/README.md`](ml/README.md) for full ML integration specifications.

---

## 10. ESP32 Hardware Integration Guide

The ESP32 firmware communicates with the backend over standard Wi-Fi via HTTP POST:

- **Target URL**: `http://<HOST_LAN_IP>:8000/api/sensor-data`
- **Method**: `POST`
- **Header**: `Content-Type: application/json`
- **Payload**:
  ```json
  {"temperature": 28.5, "humidity": 67.2, "mq135": 742.0}
  ```

> [!IMPORTANT]
> **LAN IP Requirement**: The ESP32 is an external micro-controller on the local network. It **cannot** connect to `http://localhost:8000` or `http://127.0.0.1:8000`. You must run `ipconfig` (Windows) or `ifconfig` (Linux/macOS) to obtain your computer's local network IP (e.g. `http://192.168.1.50:8000`) and configure that IP in the ESP32 firmware.

---

## 11. Frontend Dashboard Integration Guide

Frontend monitoring dashboards (e.g. React, Next.js, Vue) can integrate seamlessly:

- **CORS Configured**: Add your frontend origin (e.g. `http://localhost:3000`) to `CORS_ORIGINS` in `.env`.
- **Live Monitoring**: Periodically poll `GET /api/latest` (e.g., every 3-5 seconds).
- **Historical Charts**: Call `GET /api/history?limit=100` to plot temperature, humidity, and gas trends over time.
- **Condition Badge**: Call `GET /api/prediction` to render real-time food freshness badges.
- **System Status Indicator**: Call `GET /api/health` to display online/offline status for the edge pipeline.

---

## 12. Future Smart Actuator / Control Extension

The backend is structured to cleanly support future actuator controls (e.g., ventilation fan, Peltier cooler, warning buzzer):

```
Sensor Data Ingestion (POST /api/sensor-data)
                 │
                 ▼
         Prediction Service
                 │
                 ▼
       [Future Decision/Control Service]
                 │
                 ├── Temperature > Threshold ──► Trigger Cooler Actuator
                 ├── Humidity > Threshold    ──► Trigger Ventilation Fan
                 └── Condition == "Spoiled"  ──► Trigger Alert Buzzer
```

Future services can be added under `services/actuator_service.py` without modifying the core sensor API contracts.

---

## 13. Automated Testing

Run the test suite using `pytest`:

```powershell
# Inside virtual environment
pytest -v
```

The test suite exercises:
- FastAPI lifespan and startup
- System health checks (`/api/health`)
- Schema validation, missing fields, out-of-bounds rejection (422)
- Server-side timestamping (ISO 8601)
- Mock and real ML prediction abstractions
- Retrieval endpoints (`/api/latest`, `/api/history`, `/api/prediction`)
- Empty database state handling (404)
