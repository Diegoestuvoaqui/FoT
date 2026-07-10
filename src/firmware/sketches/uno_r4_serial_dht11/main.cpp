// src/firmware/sketches/uno_r4_wifi_dht11/main.cpp
#include "UNOR4_SERIAL_DHT11.h"
#include "../../core/communication/SerialCommunication.h"
#include "../../core/commands/CommandParser.h"
#include "../../core/commands/CommandInvoker.h"

#define SERIAL_BAUD 115200
#define CMD_BUFFER_SIZE 128  // FIX: tamaño fijo para evitar fragmentación

UNOR4_SERIAL_DHT11 sketch;
SerialCommunication comm(SERIAL_BAUD);

void setup() {
    comm.begin();
    sketch.setCommunication(&comm);
    sketch.setup();
}

void loop() {
    sketch.loop();

    // FIX: buffer estático char[] en lugar de String
    static char buffer[CMD_BUFFER_SIZE];
    static uint8_t bufIndex = 0;

    while (comm.available()) {
        int c = comm.read();
        if (c == '\n' || c == '\r') {
            if (bufIndex > 0) {
                buffer[bufIndex] = '\0';  // terminar string
                ICommand* cmd = CommandParser::parse(buffer);
                if (cmd) {
                    CommandInvoker::executeImmediate(cmd, sketch);
                }
                bufIndex = 0;  // resetear índice
            }
        } else if (bufIndex < CMD_BUFFER_SIZE - 1) {
            buffer[bufIndex++] = (char)c;
        }
        // si bufIndex llega al límite, simplemente deja de escribir (overflow silencioso)
    }
}