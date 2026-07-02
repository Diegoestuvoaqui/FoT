// src/firmware/core/communication/ICommunication.h
#ifndef ICOMMUNICATION_H
#define ICOMMUNICATION_H

#include <stdint.h>  // FIX: necesario para uint8_t / uint16_t

class ICommunication {
public:
    virtual ~ICommunication() {}
    virtual void begin() = 0;
    virtual bool available() = 0;
    virtual int read() = 0;
    virtual void send(const char* data) = 0;
    virtual void send(const uint8_t* data, uint16_t len) {}  // FIX: añadido
    virtual bool connected() = 0;
    virtual void loop() {}
    virtual const char* name() const = 0;
};

#endif