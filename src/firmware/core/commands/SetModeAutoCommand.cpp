// src/firmware/core/commands/SetModeAutoCommand.cpp
#include "SetModeAutoCommand.h"
#include "../sketches/SketchBase.h"

bool SetModeAutoCommand::execute(SketchBase& ctx) {
    ctx.setModeAuto();
    return true;
}