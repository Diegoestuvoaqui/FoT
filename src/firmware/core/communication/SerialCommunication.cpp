// src/firmware/core/communication/SerialCommunication.cpp
#include "SerialCommunication.h"
#include <Arduino.h>

SerialCommunication::SerialCommunication(long baud) : _baud(baud) {}

void SerialCommunication::begin() {
    Serial.begin(_baud);
    while (!Serial);
}

bool SerialCommunication::available() {
    return Serial.available() > 0;
}

int SerialCommunication::read() {
    return Serial.read();
}

void SerialCommunication::send(const char* data) {
    Serial.println(data);
}

bool SerialCommunication::connected() {
    return true;
}