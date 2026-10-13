"""Export the trained Stacking Hybrid model to an optimized C++ header for ESP32.

Features:
- Zero dynamic heap allocation.
- Zero ML runtime dependency (no TensorFlow Lite Micro, no Edge Impulse).
- $O(1)$ Flash-resident (const PROGMEM) lookup table over the entire 12-bit ADC space [0..4095].
- Generates `esp32_hybrid.h` for the ESP32 firmware.
"""

from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np

from src.experiment_a import StackingHybrid, SoftVotingHybrid, SingleThresholdClassifier

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
FIRMWARE_DIR = Path(__file__).resolve().parent.parent / "firmware" / "esp32_fruit_freshness"


def generate_c_header() -> Path:
    """Generate esp32_hybrid.h from final_hybrid.pkl."""
    model_path = MODELS_DIR / "final_hybrid.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    model = joblib.load(model_path)
    adcs = np.arange(4096).reshape(-1, 1)
    probs = model.predict_proba(adcs)[:, 1]
    preds = model.predict(adcs)

    # Find exact decision boundary
    transition_idx = int(np.where(np.diff(preds) != 0)[0][0])
    threshold_boundary = transition_idx + 1  # First ADC integer predicted as SPOILED/LATE

    header_lines = [
        "#pragma once",
        "",
        "// ============================================================================",
        "// Auto-generated TinyML C++ Header: Stacking Hybrid E-Nose Model",
        "// Target: ESP32 (Xtensa 32-bit LX6) | Input: MQ135 12-bit ADC [0..4095]",
        f"// Decision Boundary Threshold: ADC >= {threshold_boundary} -> LATE (SPOILED)",
        "// Memory Model: Flash-resident const table (.rodata), 0 bytes heap allocation",
        "// ============================================================================",
        "",
        "#include <Arduino.h>",
        "",
        f"#define HYBRID_DECISION_THRESHOLD {threshold_boundary}",
        "",
        "// Precomputed 12-bit ADC probability lookup table (Flash memory)",
        "static const float HYBRID_PROB_LUT[4096] PROGMEM = {",
    ]

    # Format 8 floats per line for clean readability
    for i in range(0, 4096, 8):
        chunk = [f"{probs[j]:.6f}f" for j in range(i, min(i + 8, 4096))]
        header_lines.append("  " + ", ".join(chunk) + ",")

    header_lines.extend(
        [
            "};",
            "",
            "/**",
            " * Predict categorical stage ('EARLY' vs 'LATE') from raw MQ135 ADC.",
            " */",
            "static inline const char* predictStage(float mq135) {",
            "  int adc = (int)mq135;",
            "  if (adc < 0) adc = 0;",
            "  else if (adc > 4095) adc = 4095;",
            f"  return (adc >= HYBRID_DECISION_THRESHOLD) ? \"LATE\" : \"EARLY\";",
            "}",
            "",
            "/**",
            " * Retrieve continuous P(SPOILED) probability in O(1) constant time.",
            " */",
            "static inline float predictLateProbability(float mq135) {",
            "  int adc = (int)mq135;",
            "  if (adc < 0) adc = 0;",
            "  else if (adc > 4095) adc = 4095;",
            "  return HYBRID_PROB_LUT[adc];",
            "}",
            "",
            "/**",
            " * Compute prediction confidence score [0.50 .. 1.00].",
            " */",
            "static inline float predictConfidence(float mq135) {",
            "  float p = predictLateProbability(mq135);",
            "  return (p >= 0.5f) ? p : (1.0f - p);",
            "}",
            "",
            "/**",
            " * Compatibility wrapper matching legacy signature.",
            " */",
            "static inline const char* predictFreshness(float mq135, float temperature, float humidity) {",
            "  (void)temperature;",
            "  (void)humidity;",
            "  return predictStage(mq135);",
            "}",
            "",
        ]
    )

    content = "\n".join(header_lines)
    FIRMWARE_DIR.mkdir(parents=True, exist_ok=True)
    out_file = FIRMWARE_DIR / "esp32_hybrid.h"
    out_file.write_text(content, encoding="utf-8")

    # Also save to root esp32_fruit_freshness/ folder for backward compatibility
    root_esp = Path(__file__).resolve().parent.parent / "esp32_fruit_freshness"
    if root_esp.exists():
        (root_esp / "esp32_hybrid.h").write_text(content, encoding="utf-8")

    print(f"Exported C++ header successfully: {out_file}")
    print(f"Verified decision threshold: ADC >= {threshold_boundary}")
    return out_file


if __name__ == "__main__":
    generate_c_header()
