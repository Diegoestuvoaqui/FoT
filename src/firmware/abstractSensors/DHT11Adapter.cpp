// src/firmware/abstractSensors/DHT11Adapter.cpp
#include "DHT11Adapter.h"
//#include <cmath.h>  // FIX: cmath en lugar de math.h
#include "math.h"

DHT11Adapter::DHT11Adapter(DHT* dht, const char* name)
    : _dht(dht), _lastTemp(NAN), _lastHum(NAN) {
    _readTemp = (strcmp(name, "temp") == 0);
}

float DHT11Adapter::read() {
    // FIX: leemos ambos valores de una sola vez para evitar doble lectura del bus
    _lastTemp = _dht->readTemperature();
    _lastHum  = _dht->readHumidity();

    return _readTemp ? _lastTemp : _lastHum;
}

bool DHT11Adapter::isValid() {
    if (_readTemp) {
        // FIX: rangos ajustados a DHT11 real: 0–50 °C
        return !isnan(_lastTemp) && _lastTemp >= 0.0f && _lastTemp <= 50.0f;
    } else {
        // FIX: rangos ajustados a DHT11 real: 20–90 % HR
        return !isnan(_lastHum) && _lastHum >= 20.0f && _lastHum <= 90.0f;
    }
}

const char* DHT11Adapter::getName() {
    return _readTemp ? "temp" : "hum";
}

const char* DHT11Adapter::getUnit() {
    return _readTemp ? "C" : "%";
}