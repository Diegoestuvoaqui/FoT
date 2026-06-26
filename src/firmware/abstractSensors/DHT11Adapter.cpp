// src/firmware/abstractSensors/DHT11Adapter.cpp
#include "DHT11Adapter.h"
#include <math.h>

DHT11Adapter::DHT11Adapter(uint8_t pin, const char* name)
    : dht(pin, DHT11), pin(pin), _lastTemp(NAN), _lastHum(NAN) {
    dht.begin();
    _readTemp = (strcmp(name, "temp") == 0);
}

float DHT11Adapter::read() {
    if (_readTemp) {
        _lastTemp = dht.readTemperature();
        return _lastTemp;
    } else {
        _lastHum = dht.readHumidity();
        return _lastHum;
    }
}

bool DHT11Adapter::isValid() {
    if (_readTemp) {
        return !isnan(_lastTemp) && _lastTemp >= -10.0f && _lastTemp <= 60.0f;
    } else {
        return !isnan(_lastHum) && _lastHum >= 0.0f && _lastHum <= 100.0f;
    }
}

const char* DHT11Adapter::getName() {
    return _readTemp ? "temp" : "hum";
}

const char* DHT11Adapter::getUnit() {
    return _readTemp ? "C" : "%";
}