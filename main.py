"""Main FastAPI application entrypoint for Smart Food Storage Backend."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from config.settings import settings
from database.database import init_db
from services.prediction_service import prediction_service
from routes.sensor_routes import router as sensor_router
from routes.prediction_routes import router as prediction_router
from routes.system_routes import router as system_router

# Configure standard structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smart_food_storage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown procedures."""
    logger.info("Starting up Smart Food Storage Backend...")
    logger.info(f"Loaded configuration: ML_MODE={settings.ML_MODE}, DB={settings.DATABASE_URL}")

    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.critical(f"Database initialization failed: {exc}", exc_info=True)
        raise

    # Initialize ML model (loaded once at startup)
    try:
        prediction_service.load_model()
        logger.info(f"Prediction service initialized with status: '{prediction_service.get_status()}'")
    except Exception as exc:
        logger.error(f"Prediction service initialization warning: {exc}", exc_info=True)

    yield

    logger.info("Shutting down Smart Food Storage Backend...")


app = FastAPI(
    title="Smart Food Storage Backend",
    description=(
        "Backend service for **Edge AI-Based Multi-Sensor Fusion System for Real-Time Food "
        "Spoilage Prediction and Smart Storage Control**.\n\n"
        "Provides RESTful endpoints for ESP32 multi-sensor ingestion (Temperature, Humidity, MQ135), "
        "real-time ML spoilage inference abstraction, SQLite persistence, and frontend dashboard telemetry."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Sensor Data",
            "description": "Endpoints to ingest telemetry readings from ESP32 edge devices or test harnesses.",
        },
        {
            "name": "Predictions",
            "description": "Endpoints for querying real-time food spoilage condition predictions.",
        },
        {
            "name": "System & Telemetry",
            "description": "Subsystem health status, latest sensor readings, and historical telemetry feeds.",
        },
    ],
)

# Cross-Origin Resource Sharing (CORS) setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(sensor_router)
app.include_router(prediction_router)
app.include_router(system_router)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
