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

    void setCommunication(ICommunication* comm) {
        _comm = comm;
    }

    ICommunication* getCommunication() const {
        return _comm;
    }

    virtual void setup() = 0;
    virtual void loop() = 0;

    virtual const char* sketchId() const = 0;
    virtual const char* sketchName() const = 0;
    virtual const char* version() const { return "1.0"; }

    void send(const char* data) {
        if (_comm) _comm->send(data);
    }
};

#endif
