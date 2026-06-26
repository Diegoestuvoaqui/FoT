// src/firmware/core/commands/SetModeManualCommand.h
#ifndef SET_MODE_MANUAL_COMMAND_H
#define SET_MODE_MANUAL_COMMAND_H

#include "ICommand.h"

class SetModeManualCommand : public ICommand {
public:
    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "set_mode_manual"; }
};

#endif