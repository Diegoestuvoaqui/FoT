// src/firmware/core/commands/ICommand.h
#ifndef ICOMMAND_H
#define ICOMMAND_H

class SensorSketch;

class ICommand {
public:
    virtual ~ICommand() {}
    virtual bool execute(SensorSketch& ctx) = 0;
    virtual const char* name() const = 0;
};

#endif