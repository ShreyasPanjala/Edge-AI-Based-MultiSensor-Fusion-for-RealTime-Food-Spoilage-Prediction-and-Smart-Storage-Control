#include <Arduino.h>
#include <DHT.h>
#include "esp32_hybrid.h"

// Pin configuration for ESP32 hardware
#define MQ135_PIN 34
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define LED_PIN 13
#define BUZZER_PIN 12

DHT dht(DHT_PIN, DHT_TYPE);

void runLatencyBenchmark() {
  Serial.println("Starting 10,000-run inference latency benchmark...");
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

  Serial.println("==================================================");
  Serial.print("Total 10,000 runs elapsed: ");
  Serial.print(totalElapsedMicros);
  Serial.println(" us");
  Serial.print("Average latency per inference: ");
  Serial.print(avgLatencyPerInference, 4);
  Serial.println(" us");
  Serial.println("==================================================");
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, HIGH); // Send HIGH to turn active-low buzzer OFF

  delay(1000);
  runLatencyBenchmark();
}

void loop() {
  int mq135Raw = analogRead(MQ135_PIN);
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  const char* prediction = predictStage((float)mq135Raw);
  float lateProbability = predictLateProbability((float)mq135Raw);
  float confidence = predictConfidence((float)mq135Raw);

  // Trigger LED and Buzzer if the fruit is LATE (spoiled)
  if (strcmp(prediction, "LATE") == 0) {
    digitalWrite(LED_PIN, HIGH);   // Alert LED ON
    digitalWrite(BUZZER_PIN, LOW); // Active-low Buzzer ON
  } else {
    digitalWrite(LED_PIN, LOW);    // Alert LED OFF
    digitalWrite(BUZZER_PIN, HIGH);// Active-low Buzzer OFF
  }

  // Serial Telemetry Stream (115200 baud)
  Serial.print("MQ135: ");
  Serial.println(mq135Raw);

  Serial.print("Temperature: ");
  if (isnan(temperature)) {
    Serial.println("DHT22 read failed");
  } else {
    Serial.println(temperature);
  }

  Serial.print("Humidity: ");
  if (isnan(humidity)) {
    Serial.println("DHT22 read failed");
  } else {
    Serial.println(humidity);
  }

  Serial.print("Prediction: ");
  Serial.println(prediction);

  Serial.print("LATE probability: ");
  Serial.println(lateProbability, 4);

  Serial.print("Confidence: ");
  Serial.println(confidence, 4);

  Serial.println("---");
  delay(2000);
}
