#include "DHT11Adapter.h"
#include "math.h"

// ← NUEVO: Definir variables estáticas
float DHT11Adapter::_sharedTemp = NAN;
float DHT11Adapter::_sharedHum = NAN;
unsigned long DHT11Adapter::_lastReadMs = 0;

DHT11Adapter::DHT11Adapter(DHT* dht, const char* name)
    : _dht(dht), _lastTemp(NAN), _lastHum(NAN) {
    _readTemp = (strcmp(name, "temp") == 0);
}

float DHT11Adapter::read() {
    unsigned long now = millis();

    // ← NUEVO: Solo leer del bus si pasaron 2 segundos o nunca se leyó
    if (now - _lastReadMs >= MIN_READ_INTERVAL || isnan(_sharedTemp)) {
        _sharedTemp = _dht->readTemperature();
        _sharedHum = _dht->readHumidity();
        _lastReadMs = now;
    }

    // ← NUEVO: Retornar el valor cacheado, no leer de nuevo
    if (_readTemp) {
        _lastTemp = _sharedTemp;
        return _sharedTemp;
    } else {
        _lastHum = _sharedHum;
        return _sharedHum;
    }
}

bool DHT11Adapter::isValid() {
    // ← VOLVER a la validación original, pero con rangos amplios
    if (_readTemp) {
        return !isnan(_lastTemp) && _lastTemp >= -20.0f && _lastTemp <= 60.0f;
    } else {
        return !isnan(_lastHum) && _lastHum >= 5.0f && _lastHum <= 95.0f;
    }
}

const char* DHT11Adapter::getName() {
    return _readTemp ? "temp" : "hum";
}

const char* DHT11Adapter::getUnit() {
    return _readTemp ? "C" : "%";
}