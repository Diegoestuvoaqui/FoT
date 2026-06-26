// src/firmware/core/commands/SetThresholdsCommand.h
#ifndef SET_THRESHOLDS_COMMAND_H
#define SET_THRESHOLDS_COMMAND_H

#include "ICommand.h"

class SetThresholdsCommand : public ICommand {
private:
    float _min;
    float _max;

public:
    SetThresholdsCommand(float min, float max) : _min(min), _max(max) {}

    bool execute(SketchBase& ctx) override;
    const char* name() const override { return "set_thresholds"; }
    uint16_t toJson(char* buffer, uint16_t len) const override;
};

#endif