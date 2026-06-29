// src/firmware/sketches/dht11/DHT11Sketch.cpp
#include "DHT11Sketch.h"
#include "../../abstractSensors/DHT11Adapter.h"

DHT11Sketch::DHT11Sketch() {}

void DHT11Sketch::setup() {
    send("DHT11Sketch::setup()");

    ISensor* tempSensor = new DHT11Adapter(2, "temp");
    ISensor* humSensor = new DHT11Adapter(2, "hum");

    addSensor(tempSensor);
    addSensor(humSensor);

    SensorSketch::setup();
}

void DHT11Sketch::loop() {
    SensorSketch::loop();
}
