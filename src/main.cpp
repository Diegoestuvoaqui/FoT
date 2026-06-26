// src/main.cpp
#include <Arduino.h>
#include <ArduinoJson.h>

#include "firmware/core/communication/ICommunication.h"
#include "firmware/core/communication/SerialCommunication.h"
#include "firmware/core/communication/BluetoothCommunication.h"
#include "firmware/core/commands/CommandParser.h"
#include "firmware/core/commands/ICommand.h"
#include "firmware/core/sketches/SensorSketch.h"
#include "firmware/abstractSensors/DHT11Adapter.h"

// ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────

// Seleccionar comunicación:
// #define USE_BLUETOOTH
#define USE_USB

#ifdef USE_BLUETOOTH
    #define BT_RX_PIN 10
    #define BT_TX_PIN 11
    static BluetoothCommunication comm(BT_RX_PIN, BT_TX_PIN);
#else
    static SerialCommunication comm(115200);
#endif

// ─── VARIABLES GLOBALES ───────────────────────────────────────────────────

SensorSketch sketch;
String inputBuffer;

// ─── SETUP ─────────────────────────────────────────────────────────────────

void setup() {
    // Iniciar comunicación
    comm.begin();
    sketch.setCommunication(&comm);

    // Configurar sensores
    sketch.addSensor(new DHT11Adapter(2, "temp"));
    sketch.addSensor(new DHT11Adapter(2, "hum"));

    // Setup del sketch
    sketch.setup();

    // Info inicial
    StaticJsonDocument<128> info;
    info["status"] = "ready";
    info["comm"] = comm.name();
    info["sensors"] = sketch.getSensorCount();
    
    char buf[128];
    serializeJson(info, buf, sizeof(buf));
    comm.send(buf);
}

// ─── LOOP ──────────────────────────────────────────────────────────────────

void loop() {
    // 1. Procesar comandos entrantes
    while (comm.available()) {
        int c = comm.read();
        if (c < 0) break;
        
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                inputBuffer.trim();
                
                ICommand* cmd = CommandParser::parse(inputBuffer.c_str());
                if (cmd) {
                    cmd->execute(sketch);
                    delete cmd;
                }
                
                inputBuffer = "";
            }
        } else {
            inputBuffer += (char)c;
            if (inputBuffer.length() > 256) {
                inputBuffer = "";
            }
        }
    }

    // 2. Loop del sketch (lectura periódica)
    sketch.loop();

    // 3. Loop de comunicación (si necesita mantener conexión)
    comm.loop();
}