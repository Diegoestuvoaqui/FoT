// src/firmware/sketches/esp32_wifi_dht22/main.cpp
#include <Arduino.h>
#include "ESP32_WIFI_DHT22.h"
#include "../../core/communication/ESP32WiFiCommunication.h"
#include "../../core/commands/CommandParser.h"
#include "../../core/commands/CommandInvoker.h"
#include "secrets.h"

#define CMD_BUFFER_SIZE 256

ESP32_WIFI_DHT22 sketch;

String makeBoardId() {
    uint64_t mac = ESP.getEfuseMac();
    char id[24];
    snprintf(id, sizeof(id), "esp32-%04X%08X",
             (unsigned int)(mac >> 32), (unsigned int)(mac & 0xFFFFFFFFUL));
    return String(id);
}

ESP32WiFiCommunication comm(WIFI_SSID, WIFI_PASSWORD,
                            MQTT_BROKER_FALLBACK_IP, MQTT_BROKER_FALLBACK_PORT,
                            makeBoardId().c_str());

void setup() {
    Serial.begin(115200);
    unsigned long start = millis();
    while (!Serial && (millis() - start < 3000)) {
        ;
    }

    Serial.print("Nodo: ");
    Serial.println(makeBoardId());

    comm.begin();
    sketch.setCommunication(&comm);
    sketch.setup();
}

void loop() {
    comm.loop();
    sketch.loop();

    static bool identifySent = false;
    if (!identifySent && comm.connected()) {
        identifySent = true;
        ICommand* cmd = CommandParser::parse("identify");
        if (cmd) {
            CommandInvoker::executeImmediate(cmd, sketch);
        }
        Serial.println("MQTT conectado e identificado.");
    }

    static char buffer[CMD_BUFFER_SIZE];
    static uint8_t bufIndex = 0;

    while (comm.available()) {
        int c = comm.read();
        if (c == '\n' || c == '\r') {
            if (bufIndex > 0) {
                buffer[bufIndex] = '\0';
                ICommand* cmd = CommandParser::parse(buffer);
                if (cmd) {
                    CommandInvoker::executeImmediate(cmd, sketch);
                }
                bufIndex = 0;
            }
        } else if (bufIndex < CMD_BUFFER_SIZE - 1) {
            buffer[bufIndex++] = (char)c;
        }
    }
}