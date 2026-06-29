// src/firmware/core/commands/CommandInvoker.h
#ifndef COMMAND_INVOKER_H
#define COMMAND_INVOKER_H

#include <stdint.h>
#include "ICommand.h"

#define MAX_COMMAND_QUEUE 8

class CommandInvoker {
private:
    ICommand* _queue[MAX_COMMAND_QUEUE];
    uint8_t _head;
    uint8_t _tail;
    uint8_t _count;

public:
    CommandInvoker();

    bool enqueue(ICommand* cmd);

    bool executeNext(SensorSketch& ctx);

    static bool executeImmediate(ICommand* cmd, SensorSketch& ctx);

    void clear();

    bool isEmpty() const { return _count == 0; }
};

#endif