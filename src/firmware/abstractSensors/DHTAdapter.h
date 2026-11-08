// src/firmware/abstractSensors/DHTAdapter.h
// Adaptador genérico para sensores DHT (DHT11 y DHT22).
#ifndef DHT_ADAPTER_H
#define DHT_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>

class DHTAdapter : public ISensor {
private:
    DHT* _dht;
    uint8_t _model;
    float _minValid;
    float _maxValid;
    bool _readTemp;
    float _lastValue;

    static float _sharedTemp;
    static float _sharedHum;
    static unsigned long _lastReadMs;
    static const unsigned long MIN_READ_INTERVAL = 2000;

public:
    DHTAdapter(DHT* dht, const char* name, uint8_t model);

    float read() override;
    bool isValid() override;
    const char* getName() override;
    const char* getUnit() override;
};

#endif