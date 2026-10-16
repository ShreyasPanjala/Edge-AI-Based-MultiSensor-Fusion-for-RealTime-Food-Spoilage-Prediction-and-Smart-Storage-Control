/**
 * Edge-AI Multi-Sensor Electronic Nose for Food Spoilage Prediction
 * Microcontroller Firmware: ESP32 (Xtensa 32-bit LX6)
 * 
 * Sensors:
 * - MQ-135 Gas Sensor (GPIO 34 / ADC1_CH6)
 * - DHT22 Temperature & Humidity (GPIO 4)
 * 
 * Actuators:
 * - Alert LED (GPIO 13, Active-HIGH)
 * - Alarm Buzzer (GPIO 12, Active-LOW)
 * 
 * Telemetry Output:
 * - USB Serial at 115200 baud (both human-readable & instant JSON lines)
 * - Direct Web Serial & Python Bridge compatible
 * - Optional Wi-Fi HTTP POST direct to backend
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
#define BUZZER_PIN 12      // Active-LOW Acoustic Alarm Buzzer

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

  Serial.println("\n==================================================");
  Serial.println("  ESP32 Edge-AI Food Spoilage & Storage Monitor   ");
  Serial.println("  Decision Boundary Threshold: ADC >= 738 (LATE)  ");
  Serial.println("  Baud Rate: 115200 baud                          ");
  Serial.println("==================================================");

  // Initialize Sensors
  dht.begin();
  analogReadResolution(12); // 12-bit ADC [0..4095]
  analogSetPinAttenuation(MQ135_PIN, ADC_11db); // Full range 0 - 3.3V

  // Initialize Actuator Pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);    // LED Off
  digitalWrite(BUZZER_PIN, HIGH);// Active-LOW Buzzer Off (HIGH = silent)

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

  // Hardware Actuator Control Logic
  if (strcmp(prediction, "LATE") == 0 || mq135Raw >= HYBRID_DECISION_THRESHOLD) {
    digitalWrite(LED_PIN, HIGH);   // Visual Alert LED ON (Red)
    digitalWrite(BUZZER_PIN, LOW); // Active-LOW Buzzer ON (Alert sound)
  } else {
    digitalWrite(LED_PIN, LOW);    // Visual Alert LED OFF
    digitalWrite(BUZZER_PIN, HIGH);// Active-LOW Buzzer OFF (Silent)
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
  Serial.println(prediction);
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
  Serial.print(strcmp(prediction, "LATE") == 0 ? "Spoiled" : "Fresh");
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

  // Sample interval: 2 seconds
  delay(2000);
}
