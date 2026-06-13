#ifndef STATEIRRIGATING_H
#define STATEIRRIGATING_H

#include "IState.h"

class StateIrrigating : public IState {
private:
    bool cameFromAuto;
    unsigned long startTime;
    bool firstTick;
    unsigned long lastSensorUpdate; // ← nueva
    static const unsigned long SENSOR_READ_INTERVAL = 2000;

public:
    StateIrrigating(bool autoOrigin);

    void handle(StateMachine &ctx) override;

    const char *name() const override;
};

#endif
