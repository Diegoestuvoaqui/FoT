#ifndef MOCK_SENSOR_H
#define MOCK_SENSOR_H

#include "ISensor.h"

class MockSensor : public ISensor {
private:
    SensorType _type;
    float      _value;
    bool       _valid;
    const char* _unit;

public:
    MockSensor(SensorType type, const char* unit = "%")
        : _type(type), _value(0.0f), _valid(true), _unit(unit) {}

    void setValue(float v) { _value = v; }
    void setValid(bool v)  { _valid = v; }

    float       read()        override { return _value; }
    bool        isValid()     override { return _valid; }
    SensorType  getType()     override { return _type;  }
    const char* getUnitPGM()  override { return _unit;  }
};

#endif