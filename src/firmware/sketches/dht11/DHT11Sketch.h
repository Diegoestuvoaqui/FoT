// src/firmware/sketches/dht11/DHT11Sketch.h
#ifndef DHT11_SKETCH_H
#define DHT11_SKETCH_H

#include "../../core/sketches/SensorSketch.h"

class DHT11Sketch : public SensorSketch {
public:
    DHT11Sketch();

    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "dht11"; }
    const char* sketchName() const override { return "DHT11 Sensor"; }
    const char* version() const override { return "1.0"; }
};

#endif
