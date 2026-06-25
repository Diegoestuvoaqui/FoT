#ifndef DHT11_ADAPTER_H
#define DHT11_ADAPTER_H

#include "ISensor.h"
#include <DHT.h>

class DHT11Adapter : public ISensor {
private:
    DHT dht;
    uint8_t pin;
    SensorType readingType;
    float _lastValue;

    static const char unitCelsius[] PROGMEM;
    static const char unitPercent[] PROGMEM;

public:
    // readingType: SENSOR_DHT11_TEMP o SENSOR_DHT11_HUM
    DHT11Adapter(uint8_t pin, SensorType readingType);

    float read() override;

    bool isValid() override;

    SensorType getType() override;

    const char *getUnitPGM() override;
};

#endif
