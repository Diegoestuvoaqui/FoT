// src/firmware/core/commands/IrrigateCommand.cpp
#include "IrrigateCommand.h"
#include "../sketches/SketchBase.h"

bool IrrigateCommand::execute(SketchBase& ctx) {
    ctx.turnRelayOn();
    return true;
}