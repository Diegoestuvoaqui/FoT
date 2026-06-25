// src/main.cpp
#ifdef ARDUINO
#include <Arduino.h>
#else
#include "ArduinoMock.h"
#endif
#include <ArduinoJson.h>
#include "firmware/abstractSensors/SensorFactory.h"
#include "firmware/abstractSensors/SensorType.h"
#include "firmware/stateMachine/StateMachine.h"

StateMachine fsm;
String inputBuffer = "";

// ─── Prototipo de la función ───────────────────────────────────────────────
void procesarComando(const String &cmd);

void setup() {
    Serial.begin(115200);
    while (!Serial);

    Serial.println(F("FoT - Firmware DHT11 + Relay (USB)"));

    ISensor *tempSensor = SensorFactory::create(SENSOR_DHT11_TEMP, 2);
    ISensor *humSensor = SensorFactory::create(SENSOR_DHT11_HUM, 2);

    if (tempSensor) fsm.addSensor(tempSensor);
    else Serial.println(F("ERROR: sensor temperatura no creado"));

    if (humSensor) fsm.addSensor(humSensor);
    else Serial.println(F("ERROR: sensor humedad aire no creado"));

    fsm.applyStartupState();

    Serial.print(F("Estado inicial: "));
    Serial.println(fsm.getCurrentStateName());
    Serial.println(F(
        "Comandos: irrigate, stop, auto, manual, reset_fault, enable <sensor>, disable <sensor>, th <min> <max>"));
}

void loop() {
    fsm.tick();

    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n') {
            procesarComando(inputBuffer);
            inputBuffer = "";
        } else {
            inputBuffer += c;
        }
    }

    delay(10);
}

void procesarComando(const String &line) {
    String cmd = line;
    cmd.trim();
    if (cmd.length() == 0) return;

    // ── Modo JSON (viene de SerialBridge de la estación Python) ──────────
    if (cmd.startsWith("{")) {
        JsonDocument doc;
        DeserializationError err = deserializeJson(doc, cmd);
        if (err) {
            Serial.println(F("{\"error\":\"json_parse\"}"));
            return;
        }

        const char *c = doc["cmd"] | "";

        if (strcmp(c, "irrigate") == 0) {
            fsm.dispatchCommand("irrigate");
        } else if (strcmp(c, "stop") == 0) {
            fsm.dispatchCommand("stop");
        } else if (strcmp(c, "set_mode_auto") == 0) {
            fsm.dispatchCommand("set_mode_auto");
        } else if (strcmp(c, "set_mode_manual") == 0) {
            fsm.dispatchCommand("set_mode_manual");
        } else if (strcmp(c, "reset_fault") == 0) {
            fsm.dispatchCommand("reset_fault");
        } else if (strcmp(c, "set_thresholds") == 0) {
            float minVal = doc["min"] | 30.0f;
            float maxVal = doc["max"] | 70.0f;
            fsm.dispatchCommand("set_thresholds", nullptr, minVal, maxVal);
        } else if (strcmp(c, "enable_sensor") == 0) {
            const char *sensor = doc["sensor"] | "";
            fsm.dispatchCommand("enable_sensor", sensor);
        } else if (strcmp(c, "disable_sensor") == 0) {
            const char *sensor = doc["sensor"] | "";
            fsm.dispatchCommand("disable_sensor", sensor);
        } else {
            Serial.println(F("{\"error\":\"unknown_cmd\"}"));
        }
        return;
    }

    // ── Modo texto plano (útil para debug manual desde el Serial Monitor) ─
    Serial.print(F("Comando: "));
    Serial.println(cmd);

    if (cmd == "irrigate")            fsm.dispatchCommand("irrigate");
    else if (cmd == "stop")           fsm.dispatchCommand("stop");
    else if (cmd == "auto")           fsm.dispatchCommand("set_mode_auto");
    else if (cmd == "manual")         fsm.dispatchCommand("set_mode_manual");
    else if (cmd == "reset_fault")    fsm.dispatchCommand("reset_fault");
    else if (cmd.startsWith("enable ")) {
        String sensor = cmd.substring(7);
        fsm.dispatchCommand("enable_sensor", sensor.c_str());
    } else if (cmd.startsWith("disable ")) {
        String sensor = cmd.substring(8);
        fsm.dispatchCommand("disable_sensor", sensor.c_str());
    } else if (cmd.startsWith("th ")) {
        float minVal, maxVal;
        if (sscanf(cmd.c_str() + 3, "%f %f", &minVal, &maxVal) == 2) {
            fsm.dispatchCommand("set_thresholds", nullptr, minVal, maxVal);
        } else {
            Serial.println(F("Formato: th <min> <max>"));
        }
    } else {
        Serial.println(F("Comando no reconocido"));
    }
}
