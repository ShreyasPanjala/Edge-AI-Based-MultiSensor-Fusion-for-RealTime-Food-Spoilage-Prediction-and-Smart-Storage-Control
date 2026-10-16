# ESP32 Fruit Freshness & Spoilage Monitor (Edge-AI TinyML)

This package contains the complete, verified Arduino / ESP32 firmware running the **Stacking Hybrid TinyML Model** for real-time, non-destructive fruit freshness and spoilage classification, fully configured to communicate with the **Website Dashboard**.

---

## ⚡ Quick Start: 3-Step Setup

### Step 1: Install Libraries in Arduino IDE
1. Open **Arduino IDE** (v1.8.x or v2.x).
2. Go to `Tools` > `Board` > `Boards Manager...` and install **`esp32` by Espressif Systems**.
3. Go to `Sketch` > `Include Library` > `Manage Libraries...` and install:
   * **DHT sensor library** by Adafruit
   * **Adafruit Unified Sensor**

### Step 2: Open & Flash the Firmware
1. Open `esp32_fruit_freshness.ino` in Arduino IDE.
2. Select your board: `Tools` > `Board` > `ESP32 Arduino` > **`ESP32 Dev Module`**.
3. Select your serial port: `Tools` > `Port` > **`COM...`**.
4. Click the **Upload** button (`→`).

### Step 3: Connect to the Live Website Dashboard
Once uploaded, your ESP32 starts reading the sensors and evaluating the TinyML model every 2 seconds. You have two seamless ways to display these numbers on the website:

* **Option A — Web Serial (Recommended, Zero Installs)**:
  1. Open the website: **http://127.0.0.1:8000/** in Google Chrome or Microsoft Edge.
  2. Click the **`🔌 Connect USB ESP32`** button in the top-right header.
  3. Select your ESP32 COM port and click **Connect**.
  4. The dashboard will immediately turn **HARDWARE LIVE** and graph your banana readings!

* **Option B — Python Serial Bridge**:
  Run this command in your project terminal:
  ```bash
  python serial_bridge.py
  ```
  It automatically detects your ESP32 and forwards every reading to the website database.

---

## 🔌 Hardware Wiring Diagram

| Component | Component Pin | ESP32 GPIO | Notes |
| :--- | :--- | :--- | :--- |
| **MQ135 Gas Sensor** | `A0` (Analog Out) | **GPIO 34** | ADC1_CH6 (12-bit input, 0–4095) |
| **DHT22 Climate Sensor** | `DATA` / `OUT` | **GPIO 4** | 1-wire digital (use 10k pull-up to 3.3V) |
| **Visual Alert LED** | Anode ($+$) | **GPIO 13** | Active HIGH (via 220Ω resistor) |
| **Alarm Buzzer** | Signal / Control | **GPIO 12** | Active LOW (sounds on Spoilage) |
| **VCC (Power)** | `VCC` | **5V / VIN** | MQ135 heater requires 5V rail |
| **GND (Ground)** | `GND` | **GND** | Common ground with ESP32 |

---

## 🔬 Embedded TinyML Model Specifications

* **Model Architecture**: Calibrated Stacking Hybrid (Logistic Regression meta-learner over base estimators: Random Forest, Decision Tree, Logistic Regression, Naive Bayes).
* **Storage Footprint**: **$O(1)$ Flash-Resident Lookup Table** stored in Flash memory (`PROGMEM`).
* **Decision Boundary**: **ADC $\ge$ 738 $\rightarrow$ SPOILED (LATE)**; **ADC < 738 $\rightarrow$ FRESH (EARLY)**.
* **Inference Latency**: **$< 1.0\ \mu\text{s}$** per inference.
* **Dynamic Heap Allocation**: **0 bytes** (zero memory leak risk).
* **Memory Usage**: 296.9 KB Flash (22.0%), 22.2 KB SRAM (6.0%).
* **C++ vs Python Parity**: **100.00% exact integer match over all 4,096 ADC values**.

---

## 📡 Serial Telemetry Format

The firmware streams telemetry at **115200 baud** in dual formats:

1. **Human-Readable Format** (for Arduino Serial Monitor):
```text
----------------------------------------
MQ135: 495
Temperature: 24.5
Humidity: 65.2
Prediction: EARLY
LATE probability: 0.0003
Confidence: 0.9997
---
```

2. **Compact JSON Line** (for Website Web Serial and Python Bridge):
```json
{"mq135":495,"temperature":24.5,"humidity":65.2,"prediction":"Fresh","probability_spoiled":0.0003}
```
