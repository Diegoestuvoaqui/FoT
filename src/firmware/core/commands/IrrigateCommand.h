// src/firmware/core/commands/IrrigateCommand.h
#ifndef IRRIGATE_COMMAND_H
#define IRRIGATE_COMMAND_H

#include "ICommand.h"

class IrrigateCommand : public ICommand {
public:
    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "irrigate"; }
};

#endif