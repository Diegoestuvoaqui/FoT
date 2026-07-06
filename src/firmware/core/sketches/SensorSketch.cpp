// src/firmware/core/sketches/SensorSketch.cpp
#include "SensorSketch.h"
#include <Arduino.h>
#include <ArduinoJson.h>

SensorSketch::SensorSketch()
    : _sensorCount(0)
    , _lastReadMs(0)
    , _readIntervalMs(2000) {
    for (uint8_t i = 0; i < MAX_SENSORS; i++) {
        _sensors[i] = nullptr;
    }
}

void SensorSketch::setup() {
    send("SensorSketch::setup()");
    send("Comandos: read, interval <ms>, identify");
}

void SensorSketch::loop() {
    unsigned long now = millis();
    if (now - _lastReadMs >= _readIntervalMs) {
        _lastReadMs = now;
        readAndSend();
    }
}

void SensorSketch::addSensor(ISensor* sensor) {
    if (_sensorCount < MAX_SENSORS && sensor) {
        _sensors[_sensorCount++] = sensor;
    }
}

void SensorSketch::readAndSend() {
    JsonDocument doc;
    doc["ts"] = millis();

    JsonObject data = doc["data"].to<JsonObject>();
    bool anyValid = false;

    for (uint8_t i = 0; i < _sensorCount; i++) {
        ISensor* s = _sensors[i];
        if (!s) continue;

        float val = s->read();
        if (s->isValid()) {
            JsonObject reading = data[s->getName()].to<JsonObject>();
            reading["value"] = val;  // ← Ahora val es un número válido
            reading["unit"] = s->getUnit();
            anyValid = true;
        }
    }

    doc["valid"] = anyValid;

    char buf[256];
    serializeJson(doc, buf, sizeof(buf));
    send(buf);
}

void SensorSketch::setInterval(unsigned long ms) {
    if (ms >= 100 && ms <= 60000) {
        _readIntervalMs = ms;
    }
}