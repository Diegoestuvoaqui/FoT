#ifndef SOIL_MOISTURE_ADAPTER_H
#define SOIL_MOISTURE_ADAPTER_H

#include "ISensor.h"

class SoilMoistureAdapter : public ISensor {
private:
  uint8_t analogPin;
  int dryValue;     // valor ADC en seco (típ. 800)
  int wetValue;     // valor ADC saturado (típ. 300)
  int _rawValue;    // última lectura ADC cruda
  float _lastValue; // humedad en %

  static const char unitPercent[] PROGMEM;

public:
  SoilMoistureAdapter(uint8_t analogPin, int dryValue, int wetValue);

  float read() override;
  bool isValid() override;
  SensorType getType() override;
  const char* getUnitPGM() override;
};

#endif