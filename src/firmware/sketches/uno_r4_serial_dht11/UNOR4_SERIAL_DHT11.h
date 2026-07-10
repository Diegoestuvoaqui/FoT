// src/firmware/sketches/uno_r4_wifi_dht11/UNOR4_SERIAL_DHT11.h
#ifndef DHT11_SKETCH_H
#define DHT11_SKETCH_H

#include "../../core/sketches/SensorSketch.h"

class UNOR4_SERIAL_DHT11 : public SensorSketch {
public:
    UNOR4_SERIAL_DHT11();

    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "dht11"; }
    const char* sketchName() const override { return "DHT11 Sensor"; }
    const char* version() const override { return "1.0"; }
};

#endif
