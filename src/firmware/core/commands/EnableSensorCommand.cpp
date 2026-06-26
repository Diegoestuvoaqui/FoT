// src/firmware/core/commands/EnableSensorCommand.cpp
#include "EnableSensorCommand.h"
#include "../sketches/SketchBase.h"

bool EnableSensorCommand::execute(SketchBase& ctx) {
    ctx.enableSensor(_sensor);
    return true;
}