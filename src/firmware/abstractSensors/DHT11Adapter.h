#ifndef DHT11_ADAPTER_H
#define DHT11_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>

class DHT11Adapter : public ISensor {
private:
    DHT* _dht;
    uint8_t _pin;
    float _lastTemp;
    float _lastHum;
    bool _readTemp;

    // ← NUEVO: Cache compartido entre todas las instancias
    static float _sharedTemp;
    static float _sharedHum;
    static unsigned long _lastReadMs;
    static const unsigned long MIN_READ_INTERVAL = 2000; // 2 segundos

public:
    DHT11Adapter(DHT* dht, const char* name);

    float read() override;
    bool isValid() override;
    const char* getName() override;
    const char* getUnit() override;
};

#endif