// src/firmware/core/communication/SerialCommunication.h
#ifndef SERIAL_COMMUNICATION_H
#define SERIAL_COMMUNICATION_H

#include "ICommunication.h"

class SerialCommunication : public ICommunication {
private:
    long _baud;

public:
    explicit SerialCommunication(long baud = 115200);
    void begin() override;
    bool available() override;
    int read() override;
    void send(const char* data) override;
    bool connected() override;
    const char* name() const override { return "usb"; }
};

#endif