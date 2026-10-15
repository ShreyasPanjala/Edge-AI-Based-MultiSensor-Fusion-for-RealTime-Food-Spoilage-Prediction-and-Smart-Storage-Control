# ESP32 Fruit Freshness & Spoilage Monitor (Edge-AI TinyML)

This folder contains the complete, verified Arduino / ESP32 firmware running the latest **Stacking Hybrid TinyML Model** for real-time, non-destructive fruit freshness and spoilage classification.

---

## 🚀 Quick Start: Flashing with Arduino IDE

### 1. Requirements
* **Arduino IDE** (v1.8.x or v2.x) or **PlatformIO** / **arduino-cli**
* **ESP32 Board Core**: In Arduino IDE, go to `Tools` > `Board` > `Boards Manager...` and install `esp32 by Espressif Systems` (v2.x or v3.x).
* **Required Library**: Go to `Sketch` > `Include Library` > `Manage Libraries...` and install:
  * **DHT sensor library** by Adafruit (v1.4.x)
  * *(Optional)* **Adafruit Unified Sensor**

### 2. Open & Configure
1. Extract this zip file.
2. Open `esp32_fruit_freshness.ino` in Arduino IDE.
3. In `Tools` menu, configure:
   * **Board**: `"ESP32 Dev Module"` (or your specific ESP32 board)
   * **Upload Speed**: `921600` or `115200`
   * **Flash Frequency**: `80MHz`
   * **Port**: Select the COM port connected to your ESP32

### 3. Hardware Wiring Diagram

| Component | ESP32 Pin | Details |
|---|---|---|
| **MQ135 Gas Sensor (AOUT)** | **GPIO 34** | 12-bit ADC input (`ADC1_CH6`) |
| **DHT22 Data Pin** | **GPIO 4** | Digital 1-wire (requires 10k pull-up to 3.3V) |
| **Alert LED (Anode +)** | **GPIO 13** | Active HIGH (lights up on Spoilage / LATE) |
| **Acoustic Buzzer (Control)**| **GPIO 12** | Active LOW (sounds alarm on Spoilage / LATE) |
| **VCC (All Sensors)** | **3.3V or 5V** | MQ135 heater requires 5V; DHT22 runs on 3.3V |
| **GND (All Sensors)** | **GND** | Common ground with ESP32 |

---

## 📊 Embedded Model Specs

* **Model Type**: Stacking Hybrid TinyML Classifier (compiled to $O(1)$ Flash-resident LUT).
* **Decision Boundary**: `ADC >= 738` $\rightarrow$ `LATE` (SPOILED).
* **Inference Latency**: **$< 1.0\ \mu\text{s}$** per inference.
* **Dynamic Heap Allocation**: **0 bytes** (zero memory fragmentation risk).
* **Flash Usage**: 296,972 bytes (22.0% of 1.31 MB).
* **SRAM Usage**: 22,212 bytes (6.0% of 327.68 KB).
* **Accuracy**: **99.99%** holdout / **95.81%** cross-day LODO.

---

## 🖥️ Serial Monitor Telemetry

Open the Serial Monitor at **115200 baud**.
Upon boot, the firmware runs a 10,000-iteration hardware latency benchmark, then streams telemetry every 2 seconds:

```text
MQ135: 785
Temperature: 24.50
Humidity: 62.30
Prediction: LATE
LATE probability: 0.9993
Confidence: 0.9993
---
```
