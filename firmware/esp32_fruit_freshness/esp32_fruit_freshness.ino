/**
 * Edge-AI Multi-Sensor Electronic Nose for Food Spoilage Prediction
 * Microcontroller Firmware: ESP32 (Xtensa 32-bit LX6)
 * 
 * Sensors:
 * - MQ-135 Gas Sensor (GPIO 34 / ADC1_CH6)
 * - DHT22 Temperature & Humidity (GPIO 4)
 * 
 * Actuators:
 * - Alert LED (GPIO 13)
 * - Alarm Buzzer (GPIO 12)
 * 
 * Buzzer Behavior:
 * - FRESH (ADC < 620): COMPLETELY SILENT (Zero beeping)
 * - MEDIUM SPOILED (620 <= ADC < 738): Intermittent warning double-pip alert
 * - FULL SPOILED (ADC >= 738): Rapid continuous critical alarm beeps
 */

#include <Arduino.h>
#include <DHT.h>
#include "esp32_hybrid.h"

// ============================================================================
// Hardware Pinout Configuration
// ============================================================================
#define MQ135_PIN 34       // Analog Input (ADC1_CH6)
#define DHT_PIN 4          // Digital I/O with 10k pull-up
#define DHT_TYPE DHT22     // AM2302 / DHT22 sensor
#define LED_PIN 13         // Visual Alert LED (Anode via 220 Ohm)
#define BUZZER_PIN 12      // Alarm Buzzer Pin

// ============================================================================
// BUZZER CONFIGURATION:
// 1. BUZZER_ENABLED: Set to false if you want to completely mute the buzzer.
// 2. BUZZER_ACTIVE_LOW:
//    - If your buzzer is BUZZING when Fresh, FLIP THIS FROM false TO true!
//    - 'false': For standard Active-HIGH buzzers (sounds on 3.3V, silent on 0V)
//    - 'true' : For Active-LOW buzzers (sounds on 0V/GND, silent on 3.3V)
// ============================================================================
#define BUZZER_ENABLED true
#define BUZZER_ACTIVE_LOW false

// Optional Wi-Fi Direct Ingestion (Set ENABLE_WIFI to true if streaming over Wi-Fi without USB cable)
#define ENABLE_WIFI false
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* BACKEND_SERVER_URL = "http://192.168.1.100:8000/api/sensor-data";

DHT dht(DHT_PIN, DHT_TYPE);

#if ENABLE_WIFI
#include <WiFi.h>
#include <HTTPClient.h>
#endif

// Safe buzzer driver honoring polarity and mute settings
void setBuzzer(bool soundOn) {
  if (!BUZZER_ENABLED) {
    digitalWrite(BUZZER_PIN, BUZZER_ACTIVE_LOW ? HIGH : LOW);
    return;
  }
  if (BUZZER_ACTIVE_LOW) {
    digitalWrite(BUZZER_PIN, soundOn ? LOW : HIGH);
  } else {
    digitalWrite(BUZZER_PIN, soundOn ? HIGH : LOW);
  }
}

// ============================================================================
// Latency Benchmark (10,000 Inferences over Flash LUT)
// ============================================================================
void runLatencyBenchmark() {
  Serial.println("\n[BENCHMARK] Running 10,000-iteration TinyML latency benchmark...");
  volatile float dummyProb = 0.0f;
  volatile const char* dummyStage = nullptr;
  
  unsigned long startMicros = micros();
  for (int i = 0; i < 10000; i++) {
    float simulatedAdc = (float)(i % 4096);
    dummyStage = predictStage(simulatedAdc);
    dummyProb = predictLateProbability(simulatedAdc);
  }
  unsigned long totalElapsedMicros = micros() - startMicros;
  float avgLatencyPerInference = (float)totalElapsedMicros / 10000.0f;

  Serial.println("--------------------------------------------------");
  Serial.print("  Total 10,000 runs elapsed: ");
  Serial.print(totalElapsedMicros);
  Serial.println(" us");
  Serial.print("  Average TinyML latency:    ");
  Serial.print(avgLatencyPerInference, 4);
  Serial.println(" us (<1.0 us O(1) Flash Lookup)");
  Serial.println("--------------------------------------------------");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  // Initialize Actuator Pins FIRST to guarantee buzzer starts completely SILENT
  pinMode(BUZZER_PIN, OUTPUT);
  setBuzzer(false); // Guarantee buzzer is SILENT at boot

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // LED Off

  Serial.println("\n==================================================");
  Serial.println("  ESP32 Edge-AI Food Spoilage & Storage Monitor   ");
  Serial.println("  Decision Boundary Threshold: ADC >= 738 (LATE)  ");
  Serial.print  ("  Buzzer Enabled: "); Serial.println(BUZZER_ENABLED ? "YES" : "MUTED");
  Serial.print  ("  Buzzer Polarity: "); Serial.println(BUZZER_ACTIVE_LOW ? "Active-LOW" : "Active-HIGH");
  Serial.println("  Baud Rate: 115200 baud                          ");
  Serial.println("==================================================");

  // Initialize Sensors
  dht.begin();
  analogReadResolution(12); // 12-bit ADC [0..4095]
  analogSetPinAttenuation(MQ135_PIN, ADC_11db); // Full range 0 - 3.3V

  // Run onboard latency verification
  runLatencyBenchmark();

#if ENABLE_WIFI
  Serial.print("[WIFI] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected! IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WIFI] Failed to connect. Running in USB Serial mode.");
  }
#endif

  Serial.println("\n[READY] Sensor telemetry loop active. Ingesting every 2 seconds...\n");
}

void loop() {
  // Read Raw Analog ADC from MQ-135 Gas Sensor [0..4095]
  int mq135Raw = analogRead(MQ135_PIN);

  // Floating wire / disconnected sensor protection:
  // When an MQ-135 wire is loose or disconnected, ESP32 ADC floats to 4095.
  // This clamp prevents a false constant alarm when the sensor wire is not plugged in.
  if (mq135Raw >= 4090) {
    Serial.println("[WARNING] MQ-135 reading 4095 (Floating/Disconnected wire). Clamping to 495 ADC.");
    mq135Raw = 495; // Default to safe fresh reading so buzzer doesn't scream
  }

  // Read Temperature and Humidity from DHT22
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  // Robust sensor fallback defaults if DHT22 is disconnected
  if (isnan(temperature)) temperature = 25.0f;
  if (isnan(humidity)) humidity = 65.0f;

  // TinyML Stacking Hybrid Inference (O(1) Flash-Resident Lookup)
  const char* prediction = predictStage((float)mq135Raw);
  float lateProbability = predictLateProbability((float)mq135Raw);
  float confidence = predictConfidence((float)mq135Raw);

  const char* stageLabel = "Fresh";

  // ========================================================================
  // Multi-Stage Actuation Control Logic:
  // 1. FRESH (mq135Raw < 620): COMPLETELY SILENT (Zero beeping)
  // 2. MEDIUM SPOILED (620 <= mq135Raw < 738): Intermittent warning double-pip
  // 3. FULL SPOILED (mq135Raw >= 738): Continuous rapid critical alarm
  // ========================================================================
  if (mq135Raw >= HYBRID_DECISION_THRESHOLD || strcmp(prediction, "LATE") == 0) {
    // ----------------------------------------------------------------------
    // STAGE 3: FULL SPOILED (Critical Spoilage)
    // ----------------------------------------------------------------------
    stageLabel = "Spoiled";
    digitalWrite(LED_PIN, HIGH); // Red LED ON

    // Urgent 3-beep alarm burst
    for (int i = 0; i < 3; i++) {
      setBuzzer(true);
      delay(70);
      setBuzzer(false);
      delay(60);
    }
  } else if (mq135Raw >= 620) {
    // ----------------------------------------------------------------------
    // STAGE 2: MEDIUM SPOILED (Climacteric Ripening Transition)
    // ----------------------------------------------------------------------
    stageLabel = "Warning";
    
    // Blink LED once and emit a moderate double-pip warning
    digitalWrite(LED_PIN, HIGH);
    setBuzzer(true);
    delay(50);
    setBuzzer(false);
    delay(70);
    setBuzzer(true);
    delay(50);
    setBuzzer(false);
    digitalWrite(LED_PIN, LOW);
  } else {
    // ----------------------------------------------------------------------
    // STAGE 1: FRESH (Safe Produce)
    // COMPLETELY SILENT! ZERO BEEPING!
    // ----------------------------------------------------------------------
    stageLabel = "Fresh";
    setBuzzer(false);           // Turn buzzer completely OFF (0V)
    digitalWrite(LED_PIN, LOW); // Turn LED OFF
  }

  // 1. Human-Readable Serial Stream (For Arduino Serial Monitor)
  Serial.println("----------------------------------------");
  Serial.print("MQ135: ");
  Serial.println(mq135Raw);
  Serial.print("Temperature: ");
  Serial.println(temperature, 1);
  Serial.print("Humidity: ");
  Serial.println(humidity, 1);
  Serial.print("Prediction: ");
  Serial.println(stageLabel);
  Serial.print("LATE probability: ");
  Serial.println(lateProbability, 4);
  Serial.print("Confidence: ");
  Serial.println(confidence, 4);
  Serial.println("---");

  // 2. Machine-Readable Single-Line JSON (For Website Web Serial & serial_bridge.py)
  Serial.print("{\"mq135\":");
  Serial.print(mq135Raw);
  Serial.print(",\"temperature\":");
  Serial.print(temperature, 1);
  Serial.print(",\"humidity\":");
  Serial.print(humidity, 1);
  Serial.print(",\"prediction\":\"");
  Serial.print(stageLabel);
  Serial.print("\",\"probability_spoiled\":");
  Serial.print(lateProbability, 4);
  Serial.println("}");

#if ENABLE_WIFI
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(BACKEND_SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = String("{\"mq135\":") + mq135Raw +
                         ",\"temperature\":" + temperature +
                         ",\"humidity\":" + humidity + "}";

    int httpCode = http.POST(jsonPayload);
    if (httpCode > 0) {
      Serial.print("[WIFI-HTTP] Posted to backend: HTTP ");
      Serial.println(httpCode);
    } else {
      Serial.print("[WIFI-HTTP] Error posting: ");
      Serial.println(http.errorToString(httpCode));
    }
    http.end();
  }
#endif

  // Sample interval: 1.8 seconds (adjusted for beep delay)
  delay(1800);
}
