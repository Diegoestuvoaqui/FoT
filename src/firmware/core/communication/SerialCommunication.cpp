// src/firmware/core/communication/SerialCommunication.cpp
#include "SerialCommunication.h"
#include <Arduino.h>

SerialCommunication::SerialCommunication(long baud) : _baud(baud) {}

/* para Arduino UNO r4, usb nativo
void SerialCommunication::begin() {
    Serial.begin(_baud);
    // FIX: timeout de 3 s para no bloquear eternamente sin monitor
    unsigned long start = millis();
    while (!Serial && (millis() - start < 3000)) {
        ; // espera máximo 3 segundos
    }
}
*/

// para arduino UNO r3
void SerialCommunication::begin() {
    Serial.begin(_baud);
    // En ATmega328P no se necesita while(!Serial)
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