// test_dht11_minimo.ino
#include "DHT.h"

#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  Serial.println("DHT11 test iniciado");
  delay(2000); // Esperar estabilización
}

void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  Serial.print("Temp: ");
  Serial.print(t);
  Serial.print(" | Hum: ");
  Serial.print(h);

  if (isnan(t) || isnan(h)) {
    Serial.println(" | ERROR: NaN detectado");
  } else {
    Serial.println(" | OK");
  }

  delay(2000);
}