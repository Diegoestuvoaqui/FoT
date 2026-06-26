// src/firmware/core/communication/BluetoothCommunication.h
#ifndef BLUETOOTH_COMMUNICATION_H
#define BLUETOOTH_COMMUNICATION_H

#include "ICommunication.h"
#include <SoftwareSerial.h>

class BluetoothCommunication : public ICommunication {
private:
    SoftwareSerial _bt;
    uint8_t _rxPin;
    uint8_t _txPin;

public:
    BluetoothCommunication(uint8_t rxPin, uint8_t txPin);
    void begin() override;
    bool available() override;
    int read() override;
    void send(const char* data) override;
    bool connected() override;
    const char* name() const override { return "bluetooth"; }
};

#endif