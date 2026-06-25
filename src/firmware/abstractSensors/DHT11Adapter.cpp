#include "DHT11Adapter.h"
#include <math.h>

const char DHT11Adapter::unitCelsius[] PROGMEM = "°C";
const char DHT11Adapter::unitPercent[] PROGMEM = "%";

// Constructor: ahora sí se llama DHT11Adapter y usa DHT11
DHT11Adapter::DHT11Adapter(uint8_t pin, SensorType readingType)
    : dht(pin, DHT11), pin(pin), readingType(readingType), _lastValue(NAN) {
}

float DHT11Adapter::read() {
    if (readingType == SENSOR_DHT11_TEMP) {
        _lastValue = dht.readTemperature();
    } else if (readingType == SENSOR_DHT11_HUM) {
        _lastValue = dht.readHumidity();
    }
    return _lastValue;
}

bool DHT11Adapter::isValid() {
    if (isnan(_lastValue)) return false;
    if (readingType == SENSOR_DHT11_TEMP)
        return (_lastValue >= 0.0f && _lastValue <= 50.0f);
    else
        return (_lastValue >= 20.0f && _lastValue <= 90.0f);
}

SensorType DHT11Adapter::getType() {
    return readingType;
}

const char *DHT11Adapter::getUnitPGM() {
    return (readingType == SENSOR_DHT11_TEMP) ? unitCelsius : unitPercent;
}
