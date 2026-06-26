// src/firmware/core/communication/ICommunication.h
#ifndef ICOMMUNICATION_H
#define ICOMMUNICATION_H

class ICommunication {
public:
    virtual ~ICommunication() {}
    virtual void begin() = 0;
    virtual bool available() = 0;
    virtual int read() = 0;
    virtual void send(const char* data) = 0;
    virtual bool connected() = 0;
    virtual void loop() {}
    virtual const char* name() const = 0;
};

#endif