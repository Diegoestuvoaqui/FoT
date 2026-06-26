// src/firmware/core/sketches/SensorSketch.h
#ifndef SENSOR_SKETCH_H
#define SENSOR_SKETCH_H

#include "SketchBase.h"
#include "../../abstractSensors/ISensor.h"

#define MAX_SENSORS 4

class SensorSketch : public SketchBase {
private:
    ISensor* _sensors[MAX_SENSORS];
    uint8_t _sensorCount;
    unsigned long _lastReadMs;
    unsigned long _readIntervalMs;

public:
    SensorSketch();
    
    void setup() override;
    void loop() override;
    
    // Añadir sensores
    void addSensor(ISensor* sensor);
    
    // Leer y enviar datos
    void readAndSend();
    
    // Comandos
    void setInterval(unsigned long ms);
    
    // Info
    uint8_t getSensorCount() const { return _sensorCount; }
    
    // Identificación
    const char* sketchId() const override { return "sensor"; }
    const char* sketchName() const override { return "Sensor Base"; }
};

#endif