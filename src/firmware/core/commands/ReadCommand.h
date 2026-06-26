// src/firmware/core/commands/ReadCommand.h
#ifndef READ_COMMAND_H
#define READ_COMMAND_H

#include "ICommand.h"

class ReadCommand : public ICommand {
public:
    bool execute(SensorSketch& ctx) override;
    const char* name() const override { return "read"; }
};

#endif