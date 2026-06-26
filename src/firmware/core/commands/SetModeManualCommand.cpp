// src/firmware/core/commands/SetModeManualCommand.cpp
#include "SetModeManualCommand.h"
#include "../sketches/SketchBase.h"

bool SetModeManualCommand::execute(SketchBase& ctx) {
    ctx.setModeManual();
    return true;
}