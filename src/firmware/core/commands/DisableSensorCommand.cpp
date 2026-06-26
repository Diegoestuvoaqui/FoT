// src/firmware/core/commands/DisableSensorCommand.cpp
#include "DisableSensorCommand.h"
#include "../sketches/SketchBase.h"

bool DisableSensorCommand::execute(SketchBase& ctx) {
    ctx.disableSensor(_sensor);
    return true;
}