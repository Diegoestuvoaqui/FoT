// src/firmware/core/commands/CommandInvoker.h
#ifndef COMMAND_INVOKER_H
#define COMMAND_INVOKER_H

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

    /**
     * Encola un comando para ejecución posterior.
     * @return true si se encoló, false si cola llena
     */
    bool enqueue(ICommand* cmd);

    /**
     * Ejecuta el siguiente comando de la cola.
     * @param ctx Sketch sobre el que ejecutar
     * @return true si ejecutó algo
     */
    bool executeNext(SketchBase& ctx);

    /**
     * Ejecuta inmediatamente (sin cola).
     */
    static bool executeImmediate(ICommand* cmd, SketchBase& ctx);

    /**
     * Limpia la cola (libera memoria).
     */
    void clear();

    bool isEmpty() const { return _count == 0; }
};

#endif