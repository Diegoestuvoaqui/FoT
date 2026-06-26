// src/firmware/core/commands/IntervalCommand.h
#ifndef INTERVAL_COMMAND_H
#define INTERVAL_COMMAND_H

#include "ICommand.h"

class IntervalCommand : public ICommand {
private:
    unsigned long _ms;

public:
    explicit IntervalCommand(unsigned long ms) : _ms(ms) {}
    bool execute(SensorSketch& ctx) override;
    const char* name() const override { return "interval"; }
};

#endif