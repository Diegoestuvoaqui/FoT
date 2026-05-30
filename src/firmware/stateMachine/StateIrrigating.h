#ifndef STATEIRRIGATING_H
#define STATEIRRIGATING_H

#include "IState.h"

class StateIrrigating : public IState {
private:
    bool cameFromAuto;
    unsigned long startTime;
    bool firstTick;

public:
    StateIrrigating(bool autoOrigin);
    void handle(StateMachine& ctx) override;
    const char* name() const override;
};

#endif