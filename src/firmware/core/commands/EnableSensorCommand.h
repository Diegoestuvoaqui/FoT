// src/firmware/core/commands/EnableSensorCommand.h
#ifndef ENABLE_SENSOR_COMMAND_H
#define ENABLE_SENSOR_COMMAND_H

#include "ICommand.h"

class EnableSensorCommand : public ICommand {
private:
    char _sensor[16];

public:
    EnableSensorCommand(const char* sensor) {
        strncpy(_sensor, sensor, 15);
        _sensor[15] = '\0';
    }

    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "enable_sensor"; }
};

#endif