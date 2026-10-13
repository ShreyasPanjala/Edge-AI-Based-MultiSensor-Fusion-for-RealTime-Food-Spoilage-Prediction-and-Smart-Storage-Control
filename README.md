# Edge-AI Electronic Nose (E-Nose) for Banana Freshness Detection

A lightweight Edge-AI and TinyML fruit freshness and spoilage classification system deployed on an ESP32 microcontroller with an MQ135 gas sensor and DHT22 environmental sensor.

---

## 📌 Project Overview
This repository implements a lightweight, zero-dependency TinyML Electronic Nose designed for non-destructive, real-time banana spoilage detection. A Scikit-learn Random Forest ensemble is trained on multi-day gas emission data and transpiled directly into bare-metal C++ conditional branches (`esp32_model.h`), enabling sub-microsecond inference without TensorFlow Lite Micro or third-party edge runtimes.

---

## 🛠️ Hardware Setup
- **Microcontroller**: ESP32 (Xtensa dual-core 32-bit LX6)
- **Gas Sensor**: MQ135 Air Quality Sensor &rarr; **GPIO 34** (Analog ADC)
- **Environmental Sensor**: DHT22 Temperature & Humidity &rarr; **GPIO 4** (Digital)
- **Visual Alert**: LED &rarr; **GPIO 13** (Active HIGH on `LATE`/Spoiled)
- **Acoustic Alert**: Buzzer &rarr; **GPIO 12** (Active LOW on `LATE`/Spoiled)

---

## 📊 Dataset & Research Findings
- **Dataset**: `Food-Freshness-E-Nose-Dataset` (Banana samples over Days 1 to 5, total 82,505 observations).
- **Classes**:
  - `EARLY` (Fresh): Days 1, 2, and 3 (53,449 samples). Mean MQ135: 631.86.
  - `LATE` (Spoiled): Days 4 and 5 (29,056 samples). Mean MQ135: 1094.33.
- **Overlap Zone**: 730–855 ADC counts during Day 3 (metabolic ripening transition).

### 📈 Experimental Performance
- **Standard Stratified Holdout (75/25)**:
  - Accuracy: **98.31%**
  - Precision: **98.35%**
  - Recall: **98.31%**
  - F1-Score: **98.30%**
- **Leave-One-File-Out (LOFO) Cross-Validation**:
  - Random Forest LOFO Average: **80.15%**
  - Gaussian Naive Bayes: **83.55%**
  - Logistic Regression: **80.83%**
  - Decision Tree: **80.15%**

---

## 📂 Repository Structure
```
fruit_ml/
├── esp32_fruit_freshness/       # Arduino sketch and C++ header
│   ├── esp32_fruit_freshness.ino
│   └── esp32_model.h
├── Food-Freshness-E-Nose-Dataset/ # Benchmark CSV datasets
├── analyze.py                   # Sensor statistical distribution analysis
├── export_model.py              # Scikit-learn to C++ transpiler
├── fruit_freshness_common.py    # Common dataset loader and metrics
├── train_final_random_forest.py # Final model training and JSON summary
├── evaluate_leave_one_file_out.py # Cross-day LOFO evaluation benchmark
├── predict.py                   # Python CLI inference script
├── model.pkl                    # Serialized model artifact
├── model_summary.json           # Model configuration and evaluation metrics
└── .gitignore
```

---

## 🚀 How to Run

### Python Training & Analysis
```bash
# Analyze sensor distributions
python analyze.py

# Evaluate cross-day LOFO benchmarks
python evaluate_leave_one_file_out.py

# Train the final Random Forest model and export artifacts
python train_final_random_forest.py

# Transpile the model to C++ headers for ESP32
python export_model.py
```

### ESP32 Deployment
1. Open `esp32_fruit_freshness/esp32_fruit_freshness.ino` in Arduino IDE.
2. Ensure `DHT sensor library` by Adafruit is installed.
3. Select board `ESP32 Dev Module` and flash to device.
4. Open Serial Monitor at **115200 baud** to view real-time predictions and confidence scores.
