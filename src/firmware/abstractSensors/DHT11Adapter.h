// src/firmware/abstractSensors/DHT11Adapter.h
#ifndef DHT11_ADAPTER_H
#define DHT11_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>

class DHT11Adapter : public ISensor {
private:
    DHT* _dht;          // FIX: puntero a DHT compartido, no instancia propia
    uint8_t _pin;
    float _lastTemp;
    float _lastHum;
    bool _readTemp;     // true = temp, false = hum

public:
    // FIX: ahora recibe el DHT ya inicializado y el modo
    DHT11Adapter(DHT* dht, const char* name);

    float read() override;
    bool isValid() override;
    const char* getName() override;
    const char* getUnit() override;
};

#endif