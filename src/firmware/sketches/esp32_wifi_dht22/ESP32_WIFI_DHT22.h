// src/firmware/sketches/esp32_wifi_dht22/ESP32_WIFI_DHT22.h
#ifndef ESP32_WIFI_DHT22_H
#define ESP32_WIFI_DHT22_H

#include "../../core/sketches/SensorSketch.h"

#define DHT22_PIN 4

class ESP32_WIFI_DHT22 : public SensorSketch {
public:
    ESP32_WIFI_DHT22();

    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "esp32_wifi_dht22"; }
    const char* sketchName() const override { return "ESP32 + DHT22"; }
    const char* version() const override { return "1.0.0"; }
};

#endif