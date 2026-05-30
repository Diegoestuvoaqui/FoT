#ifndef DHT22_ADAPTER_H
#define DHT22_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>               // biblioteca de Adafruit

class DHT22Adapter : public ISensor {
private:
  DHT dht;
  uint8_t pin;
  SensorType readingType;      // TEMP o HUM
  float _lastValue;

  // Cadenas de unidad almacenadas en flash
  static const char unitCelsius[] PROGMEM;
  static const char unitPercent[] PROGMEM;

public:
  // readingType: SENSOR_DHT22_TEMP o SENSOR_DHT22_HUM
  DHT22Adapter(uint8_t pin, SensorType readingType);

  float read() override;
  bool isValid() override;
  SensorType getType() override;
  const char* getUnitPGM() override;
};

#endif