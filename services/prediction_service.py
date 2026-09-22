"""Machine Learning inference abstraction layer supporting mock and real model inference."""

import os
import logging
from typing import Optional, Any
from config.settings import settings

logger = logging.getLogger(__name__)


class PredictionService:
    """Manages ML model lifecycle and inference for food condition prediction."""

    def __init__(self):
        self.mode: str = settings.ML_MODE.lower()
        self.model_path: str = settings.MODEL_PATH
        self.model: Optional[Any] = None
        self.status: str = "mock"  # "mock", "ready", or "unavailable"

    def load_model(self) -> None:
        """Load the ML model once at application startup.

        Does not reload model per request for optimal performance.
        """
        if self.mode == "mock":
            self.status = "mock"
            logger.info("PredictionService initialized in MOCK mode. Placeholder predictions enabled.")
            return

        # Real ML model mode
        logger.info(f"Attempting to load ML model from {self.model_path}...")
        if not os.path.exists(self.model_path):
            self.status = "unavailable"
            logger.warning(
                f"Model file not found at '{self.model_path}'. "
                "PredictionService marked as 'unavailable'. Real inference cannot proceed."
            )
            return

        try:
            import joblib

            self.model = joblib.load(self.model_path)
            self.status = "ready"
            logger.info(f"ML model successfully loaded from {self.model_path}. PredictionService is 'ready'.")
        except Exception as exc:
            self.status = "unavailable"
            logger.error(f"Failed to load ML model from {self.model_path}: {exc}", exc_info=True)

    def predict_food_condition(
        self,
        temperature: float,
        humidity: float,
        mq135: float,
    ) -> str:
        """Predict food storage condition based on temperature, humidity, and MQ135 readings.

        Args:
            temperature: Ambient temperature in °C.
            humidity: Relative ambient humidity in %.
            mq135: Air quality sensor reading (ADC value or ppm).

        Returns:
            str: Predicted condition class (e.g. 'Fresh', 'Warning', 'Spoiled').
        """
        # Mock mode fallback or configured mock behavior
        if self.mode == "mock" or self.status != "ready" or self.model is None:
            return self._mock_predict(temperature, humidity, mq135)

        # Real ML Model Inference
        try:
            # Expected input: 2D array-like [temperature, humidity, mq135]
            features = [[float(temperature), float(humidity), float(mq135)]]
            prediction_result = self.model.predict(features)

            # Handle single output element (string label or numeric class)
            if hasattr(prediction_result, "__iter__") and not isinstance(prediction_result, (str, bytes)):
                raw_label = prediction_result[0]
            else:
                raw_label = prediction_result

            return str(raw_label)
        except Exception as exc:
            logger.error(f"Inference error with real model: {exc}. Falling back to controlled response.", exc_info=True)
            return "Unavailable"

    def _mock_predict(self, temperature: float, humidity: float, mq135: float) -> str:
        """Generate clearly marked, heuristic mock predictions for development and testing.

        Note:
            This is strictly a placeholder implementation to allow end-to-end testing
            of the backend before the ML team delivers the final model artifacts.
        """
        logger.debug(
            f"[MOCK PREDICTION] Processing inputs: temp={temperature}, hum={humidity}, mq135={mq135}"
        )
        # Mock heuristic to simulate reasonable state transitions during test runs:
        # High gas and high temp/hum simulate spoilage conditions.
        if mq135 > 1000.0 or (temperature > 32.0 and humidity > 80.0):
            return "Spoiled"
        elif mq135 > 600.0 or temperature > 30.0:
            return "Warning"
        else:
            return "Fresh"

    def get_status(self) -> str:
        """Return current status: 'mock', 'ready', or 'unavailable'."""
        return self.status


# Global singleton instance
prediction_service = PredictionService()


def predict_food_condition(temperature: float, humidity: float, mq135: float) -> str:
    """Module-level function interface for food condition prediction."""
    return prediction_service.predict_food_condition(temperature, humidity, mq135)
