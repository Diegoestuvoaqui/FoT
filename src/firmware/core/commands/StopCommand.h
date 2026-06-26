// src/firmware/core/commands/StopCommand.h
#ifndef STOP_COMMAND_H
#define STOP_COMMAND_H

#include "ICommand.h"

class StopCommand : public ICommand {
public:
    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "stop"; }
};

#endif