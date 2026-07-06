// src/firmware/sketches/lafvin_r3_ch340_dht11/LAFVIN_R3_CH340_DHT11_Sketch.h
#ifndef LAFVIN_R3_CH340_DHT11_SKETCH_H
#define LAFVIN_R3_CH340_DHT11_SKETCH_H

#include "../../core/sketches/SensorSketch.h"

class LAFVIN_R3_CH340_DHT11_Sketch : public SensorSketch {
public:
    LAFVIN_R3_CH340_DHT11_Sketch();

    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "lafvin_r3_ch340_dht11"; }
    const char* sketchName() const override { return "LAFVIN R3 CH340 + DHT11"; }
    const char* version() const override { return "1.0"; }
};

#endif