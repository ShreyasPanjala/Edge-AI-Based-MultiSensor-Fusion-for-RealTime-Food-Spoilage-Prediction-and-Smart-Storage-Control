"""Machine Learning inference abstraction layer connecting trained models and backend telemetry."""

import os
import logging
from typing import Optional, Any, Dict
from config.settings import settings

logger = logging.getLogger(__name__)


class PredictionService:
    """Manages ML model lifecycle and inference for real-time food condition prediction."""

    def __init__(self):
        self.mode: str = settings.ML_MODE.lower()
        self.model_path: str = settings.MODEL_PATH
        self.model: Optional[Any] = None
        self.status: str = "mock"  # "mock", "ready", or "unavailable"
        self.model_name: str = "Uninitialized"
        self.decision_threshold: float = 738.0  # Calibrated decision threshold from IEEE paper

    def load_model(self) -> None:
        """Load the ML model once at application startup.

        Supports:
        1. Stacking Hybrid model (`models/final_hybrid.pkl`)
        2. Random Forest artifact (`model.pkl`)
        3. Calibrated single-threshold fallback (ADC >= 738 -> Spoiled)
        """
        if self.mode == "mock":
            self.status = "mock"
            self.model_name = "Heuristic Mock Engine"
            logger.info("PredictionService initialized in MOCK mode.")
            return

        # Attempt to import custom classes needed for StackingHybrid unpickling
        try:
            from src.experiment_a import (
                StackingHybrid,
                SoftVotingHybrid,
                SingleThresholdClassifier,
            )
        except Exception as imp_err:
            logger.warning(f"Could not import hybrid model classes from src.experiment_a: {imp_err}")

        # Check candidate paths in priority order
        candidate_paths = [
            self.model_path,
            "./models/final_hybrid.pkl",
            "models/final_hybrid.pkl",
            "./model.pkl",
            "model.pkl",
        ]

        loaded = False
        import joblib

        for path in candidate_paths:
            if not os.path.exists(path):
                continue

            try:
                logger.info(f"Loading ML model artifact from {path}...")
                artifact = joblib.load(path)

                if isinstance(artifact, dict) and "model" in artifact:
                    # Legacy dictionary artifact (model.pkl)
                    self.model = artifact["model"]
                    self.model_name = artifact.get("model_name", "Random Forest (E-Nose)")
                    self.status = "ready"
                    loaded = True
                    logger.info(f"Loaded dict artifact '{self.model_name}' from {path}")
                    break
                else:
                    # Direct estimator (e.g. StackingHybrid in final_hybrid.pkl)
                    self.model = artifact
                    self.model_name = "Edge-AI Stacking Hybrid (Logistic Regression + Random Forest)"
                    self.status = "ready"
                    loaded = True
                    logger.info(f"Loaded Stacking Hybrid model from {path}")
                    break
            except Exception as exc:
                logger.warning(f"Failed to load artifact from {path}: {exc}")

        if not loaded:
            logger.warning("No ML model file could be loaded. Activating calibrated IEEE Decision Boundary fallback.")
            self.status = "ready"
            self.model = None
            self.model_name = "Calibrated Single-Threshold Baseline (ADC=738)"

    def predict_food_condition(
        self,
        temperature: float,
        humidity: float,
        mq135: float,
    ) -> str:
        """Predict food storage condition ('Fresh', 'Warning', or 'Spoiled')."""
        detailed = self.predict_detailed(temperature, humidity, mq135)
        return detailed["prediction"]

    def predict_detailed(
        self,
        temperature: float,
        humidity: float,
        mq135: float,
    ) -> Dict[str, Any]:
        """Compute full predictive inference, continuous probabilities, and storage actuation."""
        mq135_val = float(mq135)
        temp_val = float(temperature)
        hum_val = float(humidity)

        p_spoiled: float = 0.0

        if self.mode == "mock" or (self.status != "ready" and self.model is None):
            # Fallback mock heuristic
            if mq135_val >= self.decision_threshold or (temp_val > 30.0 and hum_val > 80.0):
                p_spoiled = 0.92
            elif mq135_val >= 630.0 or temp_val > 24.0:
                p_spoiled = 0.42
            else:
                p_spoiled = 0.05
        elif self.model is not None:
            try:
                # Shape input based on model's expected features (MQ135 univariate E-Nose)
                input_feat = [[mq135_val]]

                if hasattr(self.model, "predict_proba"):
                    probs = self.model.predict_proba(input_feat)
                    if probs.shape[1] >= 2:
                        p_spoiled = float(probs[0][1])
                    else:
                        cls = self.model.classes_[0]
                        p_spoiled = 1.0 if cls == 1 else 0.0
                elif hasattr(self.model, "predict"):
                    raw_pred = self.model.predict(input_feat)[0]
                    p_spoiled = 1.0 if (raw_pred == 1 or raw_pred == "LATE" or raw_pred == "SPOILED") else 0.0
            except Exception as exc:
                logger.error(f"Error during model inference: {exc}. Falling back to threshold boundary.")
                p_spoiled = 0.95 if mq135_val >= self.decision_threshold else 0.05
        else:
            # Calibrated baseline threshold
            p_spoiled = 0.95 if mq135_val >= self.decision_threshold else 0.05

        # Determine condition and biological ripening stage
        if p_spoiled >= 0.50 or mq135_val >= self.decision_threshold:
            condition = "Spoiled"
            stage = "LATE"
            confidence = max(p_spoiled, 0.70) * 100.0
        elif p_spoiled >= 0.20 or mq135_val >= 620.0:
            condition = "Warning"
            stage = "TRANSITION"
            confidence = (1.0 - abs(0.50 - p_spoiled)) * 100.0
        else:
            condition = "Fresh"
            stage = "EARLY"
            confidence = (1.0 - p_spoiled) * 100.0

        # Physical Actuator states (reflecting ESP32 hardware behavior)
        alert_led = "RED_PULSING" if condition == "Spoiled" else ("AMBER" if condition == "Warning" else "GREEN")
        buzzer_active = True if condition == "Spoiled" else False
        ventilation_active = True if (condition != "Fresh" or mq135_val > 680.0 or hum_val > 92.0) else False
        cooling_active = True if temp_val > 15.5 else False

        # Environmental storage condition diagnostics (Bananas: 13-15°C, 85-90% RH)
        if 12.5 <= temp_val <= 15.5:
            temp_desc = "Optimal banana storage (13-15°C)"
        elif temp_val > 15.5:
            temp_desc = f"Elevated temperature ({temp_val:.1f}°C) - Respiration accelerated"
        else:
            temp_desc = f"Chilling injury risk ({temp_val:.1f}°C < 13°C)"

        if 80.0 <= hum_val <= 90.0:
            hum_desc = "Optimal relative humidity (80-90%)"
        elif hum_val > 90.0:
            hum_desc = f"High humidity ({hum_val:.1f}%) - Fungal condensation risk"
        else:
            hum_desc = f"Low humidity ({hum_val:.1f}%) - Moisture loss & shriveling"

        if condition == "Fresh":
            shelf_life = "4 - 6 Days (Safe for Distribution)"
            recommendation = "Maintain chamber temperature (13-15°C) and baseline ventilation."
        elif condition == "Warning":
            shelf_life = "12 - 24 Hours (Climacteric Surge)"
            recommendation = "Volatile ethylene spike detected. Increase ventilation and prioritize for immediate dispatch/sale."
        else:
            shelf_life = "0 Days (Spoiled / Non-Consumable)"
            recommendation = "Severe VOC & fermentation gas build-up. Evacuate affected batch immediately to prevent cross-contamination."

        return {
            "prediction": condition,
            "stage": stage,
            "probability_spoiled": round(float(p_spoiled), 4),
            "confidence_score": round(float(confidence), 1),
            "mq135_adc": round(mq135_val, 1),
            "temperature": round(temp_val, 1),
            "humidity": round(hum_val, 1),
            "threshold": self.decision_threshold,
            "model_name": self.model_name,
            "status": self.status,
            "actuators": {
                "alert_led": alert_led,
                "buzzer": buzzer_active,
                "ventilation_fan": ventilation_active,
                "cooling_unit": cooling_active,
            },
            "storage_assessment": {
                "temperature_status": temp_desc,
                "humidity_status": hum_desc,
                "shelf_life_estimate": shelf_life,
                "recommended_action": recommendation,
            },
        }

    def get_status(self) -> str:
        """Return current status: 'mock', 'ready', or 'unavailable'."""
        return self.status


# Global singleton instance
prediction_service = PredictionService()


def predict_food_condition(temperature: float, humidity: float, mq135: float) -> str:
    """Module-level function interface for food condition prediction."""
    return prediction_service.predict_food_condition(temperature, humidity, mq135)
