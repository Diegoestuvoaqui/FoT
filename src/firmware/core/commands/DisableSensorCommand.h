// src/firmware/core/commands/DisableSensorCommand.h
#ifndef DISABLE_SENSOR_COMMAND_H
#define DISABLE_SENSOR_COMMAND_H

#include "ICommand.h"

class DisableSensorCommand : public ICommand {
private:
    char _sensor[16];

public:
    DisableSensorCommand(const char* sensor) {
        strncpy(_sensor, sensor, 15);
        _sensor[15] = '\0';
    }

    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "disable_sensor"; }
};

#endif