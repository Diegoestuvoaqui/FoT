#ifndef I_SENSOR_H
#define I_SENSOR_H

#include "SensorType.h"

#ifdef ARDUINO
  #include <avr/pgmspace.h>
#endif

class ISensor {
protected:
    bool _enabled = true;

public:
    virtual float read() = 0;
    virtual bool isValid() = 0;
    virtual SensorType getType() = 0;
    virtual const char* getUnitPGM() = 0;

    void setEnabled(bool v) { _enabled = v; }
    bool isEnabled() const  { return _enabled; }

    virtual ~ISensor() {}
};

#endif