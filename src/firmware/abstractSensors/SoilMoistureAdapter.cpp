#include "SoilMoistureAdapter.h"
#include <Arduino.h>

const char SoilMoistureAdapter::unitPercent[] PROGMEM = "%";

SoilMoistureAdapter::SoilMoistureAdapter(uint8_t analogPin, int dryValue, int wetValue)
  : analogPin(analogPin), dryValue(dryValue), wetValue(wetValue),
    _rawValue(0), _lastValue(0.0f) {
}

float SoilMoistureAdapter::read() {
  _rawValue = analogRead(analogPin);
  // mapeo lineal: seco -> 0%, saturado -> 100%
  // Nota: si dryValue < wetValue (invertido), map() lo maneja
  _lastValue = map(_rawValue, dryValue, wetValue, 0, 100);
  // Asegurar límites
  if (_lastValue < 0.0f) _lastValue = 0.0f;
  if (_lastValue > 100.0f) _lastValue = 100.0f;
  return _lastValue;
}

bool SoilMoistureAdapter::isValid() {
  // Valores extremos (fuera de 100..950) indican sensor desconectado/cortocircuito
  return (_rawValue > 100 && _rawValue < 950);
}

SensorType SoilMoistureAdapter::getType() {
  return SENSOR_SOIL_CAP;
}

const char* SoilMoistureAdapter::getUnitPGM() {
  return unitPercent;
}