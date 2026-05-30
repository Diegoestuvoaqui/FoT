#include "DHT22Adapter.h"
#include <math.h>  // para isnan()

// Definición de las cadenas PROGMEM
const char DHT22Adapter::unitCelsius[] PROGMEM = "°C";
const char DHT22Adapter::unitPercent[] PROGMEM = "%";

DHT22Adapter::DHT22Adapter(uint8_t pin, SensorType readingType)
  : dht(pin, DHT22), pin(pin), readingType(readingType), _lastValue(NAN) {
}

float DHT22Adapter::read() {
  // La biblioteca DHT maneja su propia temporización; se asume que no interfiere
  // con el bus UART (caso ESP-01). Si se usara SoftwareSerial, leer antes de tráfico.
  if (readingType == SENSOR_DHT22_TEMP) {
    _lastValue = dht.readTemperature();
  } else if (readingType == SENSOR_DHT22_HUM) {
    _lastValue = dht.readHumidity();
  }
  return _lastValue;
}

bool DHT22Adapter::isValid() {
  if (isnan(_lastValue)) return false;

  if (readingType == SENSOR_DHT22_TEMP) {
    return (_lastValue >= -40.0f && _lastValue <= 80.0f);
  } else { // HUM
    return (_lastValue >= 0.0f && _lastValue <= 100.0f);
  }
}

SensorType DHT22Adapter::getType() {
  return readingType;
}

const char* DHT22Adapter::getUnitPGM() {
  if (readingType == SENSOR_DHT22_TEMP) {
    return unitCelsius;
  } else {
    return unitPercent;
  }
}