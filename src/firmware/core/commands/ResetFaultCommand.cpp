// src/firmware/core/commands/ResetFaultCommand.cpp
#include "ResetFaultCommand.h"
#include "../sketches/SketchBase.h"

bool ResetFaultCommand::execute(SketchBase& ctx) {
    ctx.resetFault();
    return true;
}