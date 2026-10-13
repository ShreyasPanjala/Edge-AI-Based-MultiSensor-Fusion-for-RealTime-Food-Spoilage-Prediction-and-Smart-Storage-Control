# Edge-AI Electronic Nose (E-Nose) for Banana Freshness Detection

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Embedded: ESP32](https://img.shields.io/badge/Embedded-ESP32-red.svg)](https://www.espressif.com/)

A lightweight, rigorous Edge-AI Electronic Nose system for non-destructive fruit freshness and spoilage classification deployed on an ESP32 microcontroller with an MQ135 gas sensor and DHT22 environmental monitoring.

---

## ⚡ One-Command Reproducible Execution

Run the complete pipeline—from real data cross-validation to synthetic robustness sweeps, C++ export, and ESP32 compiler verification:

```bash
python run_all.py
```

Or execute individual stages:
```bash
# 1. Real Data Leave-One-Day-Out & D3 Transition Analysis
python -m src.experiment_a

# 2. Synthetic Simulator & Parametric Robustness Sweeps
python -m src.robustness_sweep

# 3. Transpile Stacking Hybrid Model to Flash-Resident C++ Header
python -m src.export_hybrid

# 4. Verify 100% Exact Parity over All 4096 ADC Values
python -m src.verify_export

# 5. Compile ESP32 Firmware with arduino-cli
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/esp32_fruit_freshness
```

---

## 📂 Repository Layout

```
fruit_ml/
├── data/
│   ├── raw/                           # Real banana datasets (Banana D1 - D5)
│   └── synthetic/                     # Parameterized synthetic datasets (clearly tagged)
├── src/
│   ├── data_loader.py                 # Protocol-aware dataset loader
│   ├── experiment_a.py                # LODO benchmark, nested CV, bootstrap CI, D3 analysis
│   ├── simulator.py                   # GMM + AR(1) noise + drift + DHT22 cross-sens model
│   ├── robustness_sweep.py            # Overlap, noise, and drift sensitivity sweeps
│   ├── export_hybrid.py               # Transpiler generating Flash-resident esp32_hybrid.h
│   └── verify_export.py               # Integer-for-integer parity verification [0..4095]
├── results/
│   ├── tables/                        # Markdown and CSV tables for all experiments
│   │   ├── experiment_a_lodo_summary.md
│   │   ├── experiment_a_lodo_per_day.md
│   │   ├── experiment_a_optimistic_75_25.md
│   │   ├── experiment_a_d3_transition.md
│   │   └── simulator_robustness_sweep.md
│   └── figures/                       # High-resolution publication plots
│       ├── d3_transition_probability_histogram.png
│       └── simulator_accuracy_vs_overlap.png
├── models/
│   └── final_hybrid.pkl               # Serialized Stacking Hybrid artifact
├── firmware/
│   └── esp32_fruit_freshness/
│       ├── esp32_fruit_freshness.ino  # Production ESP32 firmware with latency benchmark
│       ├── esp32_hybrid.h             # O(1) Flash-resident TinyML lookup table
│       └── esp32_model.h              # Legacy Random Forest nested branch header
├── run_all.py                         # Single-command orchestrator
├── results_summary.md                 # Detailed engineering summary of all findings
├── methods_text.md                    # Paper-ready academic methodology text
├── requirements.txt                   # Pinned dependency versions
└── README.md
```

---

## 🔬 Scientific Highlights & Headline Results

### 1. Headline LODO Benchmark (Real Data: D1, D2, D4, D5)
- **Single-Threshold Baseline**: **100.00% Mean Day Acc** (95% CI: 100.00% – 100.00%).
- **Logistic Regression**: **94.70% Mean Day Acc** (95.81% Pooled Acc).
- **Random Forest**: **76.25% Mean Day Acc** (82.76% Pooled Acc).
- **Stacking Hybrid**: **75.81% Mean Day Acc** (82.40% Pooled Acc).
- *Honest Scientific Insight*: When Day 2 is held out, unconstrained tree algorithms pick split thresholds too low ($\approx 580$), causing 86% false positive spoilage predictions. The calibrated **Single-Threshold** and **Logistic Regression** models are vastly more resilient on univariate gas sensor data.

### 2. Temporal Leakage in Random Splits
- Under a conventional **75/25 stratified random split**, all models achieve **99.61% – 100.00% accuracy**. This is documented as **optimistic** due to strong temporal autocorrelation between sequential samples in continuous sensor runs.

### 3. Transition Phase Discovery (Day 3)
- Day 3 was explicitly excluded from binary training to prevent label distortion during the metabolic climacteric ripening burst.
- Evaluated in isolation, the trained models predict **64.8% to 85.3% of Day 3 samples as SPOILED**, with mean predicted probabilities of **0.536 to 0.855**. This confirms that volatile ester/ethanol accumulation surges before visible fruit necrosis.

---

## 💻 Embedded TinyML Hardware Profile (ESP32)

| Parameter | Value | Budget | Status |
| :--- | :---: | :---: | :---: |
| **Input Space Verified** | 4,096 levels (ADC 0..4095) | 4,096 levels | **100.00% Match** |
| **Python vs C++ Discrepancies** | **0 / 4,096** | 0 | **PASSED** |
| **Flash Program Storage** | **296,972 bytes (22.0%)** | 1,310,720 bytes | **PASSED** |
| **Dynamic SRAM Memory** | **22,212 bytes (6.0%)** | 327,680 bytes | **PASSED** |
| **Dynamic Heap Usage** | **0 bytes** | 0 bytes | **PASSED (Static Flash)** |
| **Inference Latency** | **$< 1.0\ \mu\text{s}$** | $< 50\ \mu\text{s}$ | **PASSED ($O(1)$ Lookup)** |

---

## 🛠️ Hardware Wiring

- **MQ135 Gas Sensor**: Analog Out &rarr; **GPIO 34** (ADC1_CH6)
- **DHT22 Temperature & Humidity**: Data Pin &rarr; **GPIO 4** (with 10k pullup)
- **Alert LED**: Anode &rarr; **GPIO 13** (Active HIGH upon spoilage)
- **Active-Low Buzzer**: Control Pin &rarr; **GPIO 12** (Active LOW upon spoilage)
- **Serial Baud Rate**: **115200 baud**
