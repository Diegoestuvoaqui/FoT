// src/firmware/sketches/dht11/main.cpp
#include "DHT11Sketch.h"
#include "../../core/communication/SerialCommunication.h"
#include "../../core/commands/CommandParser.h"
#include "../../core/commands/CommandInvoker.h"

// --- Configuración ---
#define SERIAL_BAUD 115200

// --- Instancias globales ---
DHT11Sketch sketch;
SerialCommunication comm(SERIAL_BAUD);

void setup() {
    comm.begin();
    sketch.setCommunication(&comm);
    sketch.setup();
}

void loop() {
    sketch.loop();
    
    // Leer comandos del puerto serial y ejecutarlos
    static String buffer;
    while (comm.available()) {
        int c = comm.read();
        if (c == '\n' || c == '\r') {
            if (buffer.length() > 0) {
                ICommand* cmd = CommandParser::parse(buffer.c_str());
                if (cmd) {
                    CommandInvoker::executeImmediate(cmd, sketch);
                }
                buffer = "";
            }
        } else {
            buffer += (char)c;
        }
    }
}
