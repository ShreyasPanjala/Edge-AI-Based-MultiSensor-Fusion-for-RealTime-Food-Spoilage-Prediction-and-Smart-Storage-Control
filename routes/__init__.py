"""API routers package."""
from .sensor_routes import router as sensor_router
from .prediction_routes import router as prediction_router
from .system_routes import router as system_router

__all__ = ["sensor_router", "prediction_router", "system_router"]
