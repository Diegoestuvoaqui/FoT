#include <Arduino.h>
#include "abstractSensors/ISensor.h"
#include "abstractSensors/SensorFactory.h"
#include "abstractSensors/SensorType.h"

ISensor* sensorHumSuelo;
ISensor* sensorTemp;
ISensor* sensorHumAire;

void setup() {
  Serial.begin(9600);
  delay(2000);
  sensorHumSuelo = SensorFactory::create(SENSOR_SOIL_CAP, A0, 800, 300);
  sensorTemp     = SensorFactory::create(SENSOR_DHT22_TEMP, 2);
  sensorHumAire  = SensorFactory::create(SENSOR_DHT22_HUM, 2);
}

void loop() {
  float hs = sensorHumSuelo->read();
  float ta = sensorTemp->read();
  float ha = sensorHumAire->read();

  Serial.print("Suelo: ");
  Serial.print(hs);
  Serial.print("%  válido: ");
  Serial.print(sensorHumSuelo->isValid() ? "SI" : "NO");

  Serial.print(" | Temp: ");
  Serial.print(ta);
  char unitBuf[4];
  strcpy_P(unitBuf, sensorTemp->getUnitPGM());
  Serial.print(unitBuf);
  Serial.print("  válido: ");
  Serial.print(sensorTemp->isValid() ? "SI" : "NO");

  Serial.print(" | Hum Aire: ");
  Serial.print(ha);
  strcpy_P(unitBuf, sensorHumAire->getUnitPGM());
  Serial.print(unitBuf);
  Serial.print("  válido: ");
  Serial.println(sensorHumAire->isValid() ? "SI" : "NO");

  delay(2000);
}