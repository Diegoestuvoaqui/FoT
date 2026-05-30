#ifndef STATEFAULT_H
#define STATEFAULT_H

#include "IState.h"

class StateFault : public IState {
private:
    const char* faultType; // "sensor_invalid" o "irrigation_timeout"

public:
    StateFault(const char* type);
    void handle(StateMachine& ctx) override;
    const char* name() const override; 
};

#endif