// src/firmware/core/commands/SetModeAutoCommand.h
#ifndef SET_MODE_AUTO_COMMAND_H
#define SET_MODE_AUTO_COMMAND_H

#include "ICommand.h"

class SetModeAutoCommand : public ICommand {
public:
    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "set_mode_auto"; }
};

#endif