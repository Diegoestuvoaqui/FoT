// src/firmware/core/commands/ReadCommand.cpp
#include "ReadCommand.h"
#include "../sketches/SensorSketch.h"

bool ReadCommand::execute(SensorSketch& ctx) {
    ctx.readAndSend();
    return true;
}