#include <Arduino.h>
#include <DHT.h>
#include "esp32_model.h"

// Adjust these pins for your wiring.
#define MQ135_PIN 34
#define DHT_PIN 4
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
}

void loop() {
  int mq135Raw = analogRead(MQ135_PIN);
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  const char* prediction = predictStage((float)mq135Raw);
  float lateProbability = predictLateProbability((float)mq135Raw);
  float confidence = predictConfidence((float)mq135Raw);

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
