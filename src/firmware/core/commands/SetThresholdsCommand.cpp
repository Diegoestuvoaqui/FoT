// src/firmware/core/commands/SetThresholdsCommand.cpp
#include "SetThresholdsCommand.h"
#include "../sketches/SketchBase.h"
#include <stdio.h>

bool SetThresholdsCommand::execute(SketchBase& ctx) {
    ctx.setThresholds(_min, _max);
    return true;
}

uint16_t SetThresholdsCommand::toJson(char* buffer, uint16_t len) const {
    return snprintf(buffer, len, "{\"cmd\":\"set_thresholds\",\"min\":%.1f,\"max\":%.1f}", _min, _max);
}