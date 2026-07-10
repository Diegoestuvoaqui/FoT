// src/firmware/sketches/uno_r4_wifi_dht11/main.cpp
// Version WiFi: publica lecturas del DHT11 por MQTT (WiFiS3 + PubSubClient)
// Requiere que el broker MQTT sea alcanzable desde la red WiFi configurada.

#include "UNOR4_WIFI_DHT11.h"
#include "../../core/communication/WiFiCommunication.h"
#include "../../core/commands/CommandParser.h"
#include "../../core/commands/CommandInvoker.h"

// ---- Configuración de red / MQTT ----
// TODO: ajustar a tu entorno (o mover a un config.h que no se suba a git)
#define WIFI_SSID      "TU_SSID"
#define WIFI_PASSWORD  "TU_PASSWORD"
#define MQTT_BROKER_IP "192.168.1.100"
#define MQTT_BROKER_PORT 1883
#define PARCELA_ID     "parcela01"

#define CMD_BUFFER_SIZE 128

UNOR4_WIFI_DHT11 sketch;
WiFiCommunication comm(WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER_IP, MQTT_BROKER_PORT, PARCELA_ID);

void setup() {
    Serial.begin(115200); // solo para depuración local por USB
    unsigned long start = millis();
    while (!Serial && (millis() - start < 3000)) {
        ; // esperar max 3s al monitor serie (no bloquea si no hay uno conectado)
    }

    Serial.println("Conectando WiFi + MQTT...");
    comm.begin(); // conecta WiFi y configura el cliente MQTT

    if (comm.connectMQTT()) {
        Serial.println("MQTT conectado.");
    } else {
        Serial.println("MQTT: fallo de conexion inicial, se reintentara en loop().");
    }

    sketch.setCommunication(&comm);
    sketch.setup();
}

void loop() {
    // Mantiene viva la conexion WiFi/MQTT y reconecta si se cae
    comm.loop();

    // Lecturas periodicas del DHT11 -> publica en fot/<parcela>/sensores
    sketch.loop();

    // Procesa comandos recibidos por MQTT en fot/<parcela>/control
    // (interval <ms>, read, identify), llegan como texto vía appendToBuffer()
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
        // overflow silencioso si se excede el buffer, igual que en las otras variantes
    }
}
