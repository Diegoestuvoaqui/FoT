// src/firmware/sketches/uno_r3_dht11/UNOR3_DHT11_Sketch.cpp
#include "UNOR3_DHT11_Sketch.h"
#include "../../abstractSensors/DHT11Adapter.h"
#include <DHT.h>

UNOR3_DHT11_Sketch::UNOR3_DHT11_Sketch() {}

void UNOR3_DHT11_Sketch::setup() {
    send("UNOR3_DHT11_Sketch::setup()");

    // Un solo DHT compartido entre ambos sensores
    static DHT dht(2, DHT11);
    dht.begin();

    ISensor* tempSensor = new DHT11Adapter(&dht, "temp");
    ISensor* humSensor  = new DHT11Adapter(&dht, "hum");

    addSensor(tempSensor);
    addSensor(humSensor);

    SensorSketch::setup();
}

void UNOR3_DHT11_Sketch::loop() {
    SensorSketch::loop();
}