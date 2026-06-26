// src/firmware/abstractSensors/DHT11Adapter.h
#ifndef DHT11_ADAPTER_H
#define DHT11_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>

class DHT11Adapter : public ISensor {
private:
    DHT dht;
    uint8_t pin;
    float _lastTemp;
    float _lastHum;
    bool _readTemp;  // true = temp, false = hum

public:
    // name: "temp" o "hum"
    DHT11Adapter(uint8_t pin, const char* name);

    float read() override;
    bool isValid() override;
    const char* getName() override;
    const char* getUnit() override;
};

#endif