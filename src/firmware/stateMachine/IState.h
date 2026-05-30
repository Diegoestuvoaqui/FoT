#ifndef ISTATE_H
#define ISTATE_H

class StateMachine; // forward declaration

class IState {
public:
    virtual void handle(StateMachine& ctx) = 0;
    virtual ~IState() {}
    virtual const char* name() const = 0;
};

#endif