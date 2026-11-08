// src/firmware/sketches/esp32_wifi_dht22/ESP32_WIFI_DHT22.cpp
#include "ESP32_WIFI_DHT22.h"
#include "../../abstractSensors/DHTAdapter.h"

ESP32_WIFI_DHT22::ESP32_WIFI_DHT22() {}

void ESP32_WIFI_DHT22::setup() {
    send("ESP32_WIFI_DHT22::setup()");

    static DHT dht(DHT22_PIN, DHT22);
    dht.begin();

    addSensor(new DHTAdapter(&dht, "temp", DHT22));
    addSensor(new DHTAdapter(&dht, "hum", DHT22));

    SensorSketch::setup();
}

void ESP32_WIFI_DHT22::loop() {
    SensorSketch::loop();
}