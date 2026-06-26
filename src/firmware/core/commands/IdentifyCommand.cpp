// src/firmware/core/commands/IdentifyCommand.cpp
#include "IdentifyCommand.h"
#include "../sketches/SensorSketch.h"
#include <ArduinoJson.h>

bool IdentifyCommand::execute(SensorSketch& ctx) {
    StaticJsonDocument<128> doc;
    doc["sketch"] = ctx.sketchId();
    doc["name"] = ctx.sketchName();
    doc["version"] = ctx.version();
    doc["sensors"] = ctx.getSensorCount();
    
    char buf[128];
    serializeJson(doc, buf, sizeof(buf));
    ctx.send(buf);
    return true;
}