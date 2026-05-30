#ifndef STATEIDLE_H
#define STATEIDLE_H

#include "IState.h"

class StateIdle : public IState {
private:
    unsigned long lastSensorUpdate;
    static const unsigned long SENSOR_READ_INTERVAL = 2000; // ms

public:
    StateIdle();
    void handle(StateMachine& ctx) override;
    const char* name() const override; 
};

#endif