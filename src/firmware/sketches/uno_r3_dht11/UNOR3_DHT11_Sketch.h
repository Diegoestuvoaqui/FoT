// src/firmware/sketches/uno_r3_dht11/UNOR3_DHT11_Sketch.h
#ifndef UNO_R3_DHT11_SKETCH_H
#define UNO_R3_DHT11_SKETCH_H

#include "../../core/sketches/SensorSketch.h"

class UNOR3_DHT11_Sketch : public SensorSketch {
public:
    UNOR3_DHT11_Sketch();

    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "uno_r3_dht11"; }
    const char* sketchName() const override { return "UNO R3 + DHT11"; }
    const char* version() const override { return "1.0"; }
};

#endif