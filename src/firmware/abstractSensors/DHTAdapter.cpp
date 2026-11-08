// src/firmware/abstractSensors/DHTAdapter.cpp
#include "DHTAdapter.h"
#include <math.h>
#include <string.h>

float DHTAdapter::_sharedTemp = NAN;
float DHTAdapter::_sharedHum = NAN;
unsigned long DHTAdapter::_lastReadMs = 0;

DHTAdapter::DHTAdapter(DHT* dht, const char* name, uint8_t model)
    : _dht(dht)
    , _model(model)
    , _lastValue(NAN) {
    _readTemp = (strcmp(name, "temp") == 0);

    if (_model == DHT22) {
        _minValid = _readTemp ? -40.0f : 0.0f;
        _maxValid = _readTemp ?  80.0f : 100.0f;
    } else {
        _minValid = _readTemp ? -20.0f : 5.0f;
        _maxValid = _readTemp ?  60.0f : 95.0f;
    }
}

float DHTAdapter::read() {
    unsigned long now = millis();
    if (now - _lastReadMs >= MIN_READ_INTERVAL || isnan(_sharedTemp)) {
        _sharedTemp = _dht->readTemperature();
        _sharedHum = _dht->readHumidity();
        _lastReadMs = now;
    }
    _lastValue = _readTemp ? _sharedTemp : _sharedHum;
    return _lastValue;
}

bool DHTAdapter::isValid() {
    return !isnan(_lastValue) && _lastValue >= _minValid && _lastValue <= _maxValid;
}

const char* DHTAdapter::getName() {
    return _readTemp ? "temp" : "hum";
}

const char* DHTAdapter::getUnit() {
    return _readTemp ? "C" : "%";
}