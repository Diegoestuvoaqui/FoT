// src/firmware/abstractSensors/ISensor.h
#ifndef I_SENSOR_H
#define I_SENSOR_H

class ISensor {
public:
    virtual float read() = 0;
    virtual bool isValid() = 0;
    virtual const char* getName() = 0;
    virtual const char* getUnit() = 0;
    virtual ~ISensor() {}
};

#endif