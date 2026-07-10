// src/firmware/sketches/uno_r4_wifi_dht11/UNOR4_SERIAL_DHT11.cpp
#include "UNOR4_SERIAL_DHT11.h"
#include "../../abstractSensors/DHT11Adapter.h"

UNOR4_SERIAL_DHT11::UNOR4_SERIAL_DHT11() {}

void UNOR4_SERIAL_DHT11::setup() {
    send("DHT11Sketch::setup()");

    // FIX: un solo objeto DHT compartido entre ambos adaptadores
    static DHT dht(2, DHT11);
    dht.begin();

    ISensor* tempSensor = new DHT11Adapter(&dht, "temp");
    ISensor* humSensor  = new DHT11Adapter(&dht, "hum");

    addSensor(tempSensor);
    addSensor(humSensor);

    SensorSketch::setup();
}

void UNOR4_SERIAL_DHT11::loop() {
    SensorSketch::loop();
}