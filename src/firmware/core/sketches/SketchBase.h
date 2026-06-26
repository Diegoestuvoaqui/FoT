// src/firmware/core/sketches/SketchBase.h
#ifndef SKETCH_BASE_H
#define SKETCH_BASE_H

#include <Arduino.h>
#include "../communication/ICommunication.h"

class SketchBase {
protected:
    ICommunication* _comm;

public:
    SketchBase() : _comm(nullptr) {}
    virtual ~SketchBase() {}

    /**
     * Inyecta el medio de comunicación (Bridge).
     */
    void setCommunication(ICommunication* comm) {
        _comm = comm;
    }

    ICommunication* getCommunication() const {
        return _comm;
    }

    virtual void setup() = 0;
    virtual void loop() = 0;

    // Métodos que los comandos invocarán
    virtual void turnRelayOn() {}
    virtual void turnRelayOff() {}
    virtual void setModeAuto() {}
    virtual void setModeManual() {}
    virtual void resetFault() {}
    virtual void setThresholds(float min, float max) {
        (void)min; (void)max;
    }
    virtual void enableSensor(const char* sensorName) {
        (void)sensorName;
    }
    virtual void disableSensor(const char* sensorName) {
        (void)sensorName;
    }

    // Identificación
    virtual const char* sketchId() const = 0;
    virtual const char* sketchName() const = 0;
    virtual const char* version() const { return "1.0"; }

    // Comunicación helper
    void send(const char* data) {
        if (_comm) _comm->send(data);
    }
};

#endif