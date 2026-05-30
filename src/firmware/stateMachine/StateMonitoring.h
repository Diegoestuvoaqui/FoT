#ifndef STATEMONITORING_H
#define STATEMONITORING_H

#include "IState.h"

class StateMonitoring : public IState {
private:
    unsigned long lastSensorUpdate;
    static const unsigned long SENSOR_READ_INTERVAL = 2000; // ms

public:
    StateMonitoring();
    void handle(StateMachine& ctx) override;
    const char* name() const override;
};

#endif