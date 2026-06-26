// src/firmware/core/communication/BluetoothCommunication.cpp
#include "BluetoothCommunication.h"

BluetoothCommunication::BluetoothCommunication(uint8_t rxPin, uint8_t txPin)
    : _bt(rxPin, txPin), _rxPin(rxPin), _txPin(txPin) {}

void BluetoothCommunication::begin() {
    _bt.begin(9600);
}

bool BluetoothCommunication::available() {
    return _bt.available() > 0;
}

int BluetoothCommunication::read() {
    return _bt.read();
}

void BluetoothCommunication::send(const char* data) {
    _bt.println(data);
}

bool BluetoothCommunication::connected() {
    return true;
}