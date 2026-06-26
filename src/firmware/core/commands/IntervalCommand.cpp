// src/firmware/core/commands/IntervalCommand.cpp
#include "IntervalCommand.h"
#include "../sketches/SensorSketch.h"

bool IntervalCommand::execute(SensorSketch& ctx) {
    ctx.setInterval(_ms);
    return true;
}