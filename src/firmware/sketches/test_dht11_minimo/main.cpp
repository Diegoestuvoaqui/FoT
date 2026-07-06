// src/firmware/sketches/test_dht11_minimo/main.cpp
// Sketch mínimo de diagnóstico para DHT11 en LAFVIN R3 CH340
// NO usa el framework — accede directo al sensor para aislar problemas

#include <Arduino.h>
#include "DHT.h"

#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
    Serial.begin(115200);

    // En CH340 no hace falta while(!Serial), pero no molesta
    unsigned long start = millis();
    while (!Serial && (millis() - start < 3000)) {
        ; // Esperar max 3 segundos
    }

    Serial.println("=== DHT11 Test Minimo ===");
    Serial.print("Pin: ");
    Serial.println(DHTPIN);
    Serial.print("Tipo: DHT");
    Serial.println(DHTTYPE);

    dht.begin();
    Serial.println("dht.begin() OK");

    delay(2000);  // Esperar estabilizacion del sensor

    Serial.println("Setup completo, iniciando loop...");
    Serial.println("=========================");
}

void loop() {
    // Leer ambos valores
    float t = dht.readTemperature();
    float h = dht.readHumidity();

    Serial.print("[");
    Serial.print(millis());
    Serial.print("] ");

    Serial.print("Temp: ");
    if (isnan(t)) {
        Serial.print("NaN");
    } else {
        Serial.print(t);
    }

    Serial.print(" C | Hum: ");
    if (isnan(h)) {
        Serial.print("NaN");
    } else {
        Serial.print(h);
    }
    Serial.print(" %");

    if (isnan(t) || isnan(h)) {
        Serial.println(" | ERROR: NaN detectado");
    } else {
        Serial.println(" | OK");
    }

    delay(2500);  // DHT11 necesita minimo 2 segundos entre lecturas
}
