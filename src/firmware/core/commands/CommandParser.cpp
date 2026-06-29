// src/firmware/core/commands/CommandParser.cpp
#include "CommandParser.h"
#include "ReadCommand.h"
#include "IntervalCommand.h"
#include "IdentifyCommand.h"
#include <ArduinoJson.h>
#include <string.h>
#include <stdlib.h>

ICommand* CommandParser::parse(const char* input) {
    if (!input || strlen(input) == 0) return nullptr;

    if (input[0] == '{') {
        JsonDocument doc;
        DeserializationError err = deserializeJson(doc, input);
        if (err) return nullptr;

        const char* cmd = doc["cmd"] | "";

        if (strcmp(cmd, "read") == 0) return new ReadCommand();
        if (strcmp(cmd, "identify") == 0) return new IdentifyCommand();
        if (strcmp(cmd, "interval") == 0) {
            return new IntervalCommand(doc["ms"] | 2000);
        }
        return nullptr;
    }

    if (strcmp(input, "read") == 0) return new ReadCommand();
    if (strcmp(input, "identify") == 0) return new IdentifyCommand();

    if (strncmp(input, "interval ", 9) == 0) {
        unsigned long ms = atol(input + 9);
        return new IntervalCommand(ms);
    }

    return nullptr;
}