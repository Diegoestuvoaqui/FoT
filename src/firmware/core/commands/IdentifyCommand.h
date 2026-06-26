// src/firmware/core/commands/IdentifyCommand.h
#ifndef IDENTIFY_COMMAND_H
#define IDENTIFY_COMMAND_H

#include "ICommand.h"

class IdentifyCommand : public ICommand {
public:
    bool execute(SensorSketch& ctx) override;
    const char* name() const override { return "identify"; }
};

#endif