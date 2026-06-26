// src/firmware/core/commands/StopCommand.cpp
#include "StopCommand.h"
#include "../sketches/SketchBase.h"

bool StopCommand::execute(SketchBase& ctx) {
    ctx.turnRelayOff();
    return true;
}