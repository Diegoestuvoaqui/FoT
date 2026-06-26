// src/firmware/core/commands/CommandParser.h
#ifndef COMMAND_PARSER_H
#define COMMAND_PARSER_H

#include "ICommand.h"

class CommandParser {
public:
    static ICommand* parse(const char* input);
};

#endif