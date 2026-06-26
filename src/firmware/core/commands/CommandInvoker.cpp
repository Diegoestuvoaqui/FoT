// src/firmware/core/commands/CommandInvoker.cpp
#include "CommandInvoker.h"

CommandInvoker::CommandInvoker() : _head(0), _tail(0), _count(0) {
    for (uint8_t i = 0; i < MAX_COMMAND_QUEUE; i++) {
        _queue[i] = nullptr;
    }
}

bool CommandInvoker::enqueue(ICommand* cmd) {
    if (_count >= MAX_COMMAND_QUEUE) return false;
    _queue[_tail] = cmd;
    _tail = (_tail + 1) % MAX_COMMAND_QUEUE;
    _count++;
    return true;
}

bool CommandInvoker::executeNext(SketchBase& ctx) {
    if (_count == 0) return false;

    ICommand* cmd = _queue[_head];
    _queue[_head] = nullptr;
    _head = (_head + 1) % MAX_COMMAND_QUEUE;
    _count--;

    if (cmd) {
        cmd->execute(ctx);
        delete cmd;
        return true;
    }
    return false;
}

bool CommandInvoker::executeImmediate(ICommand* cmd, SketchBase& ctx) {
    if (!cmd) return false;
    bool ok = cmd->execute(ctx);
    delete cmd;
    return ok;
}

void CommandInvoker::clear() {
    while (_count > 0) {
        ICommand* cmd = _queue[_head];
        if (cmd) delete cmd;
        _queue[_head] = nullptr;
        _head = (_head + 1) % MAX_COMMAND_QUEUE;
        _count--;
    }
    _head = _tail = 0;
}