// src/firmware/core/commands/ResetFaultCommand.h
#ifndef RESET_FAULT_COMMAND_H
#define RESET_FAULT_COMMAND_H

#include "ICommand.h"

class ResetFaultCommand : public ICommand {
public:
    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "reset_fault"; }
};

#endif