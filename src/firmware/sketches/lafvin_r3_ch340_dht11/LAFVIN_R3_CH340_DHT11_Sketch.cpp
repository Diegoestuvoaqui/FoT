// src/firmware/sketches/lafvin_r3_ch340_dht11/LAFVIN_R3_CH340_DHT11_Sketch.cpp
#include "LAFVIN_R3_CH340_DHT11_Sketch.h"
#include "../../abstractSensors/DHT11Adapter.h"
#include <DHT.h>

LAFVIN_R3_CH340_DHT11_Sketch::LAFVIN_R3_CH340_DHT11_Sketch() {}

void LAFVIN_R3_CH340_DHT11_Sketch::setup() {
    send("LAFVIN_R3_CH340_DHT11_Sketch::setup()");

    // Un solo objeto DHT compartido entre ambos adaptadores
    static DHT dht(2, DHT11);
    dht.begin();

    ISensor* tempSensor = new DHT11Adapter(&dht, "temp");
    ISensor* humSensor  = new DHT11Adapter(&dht, "hum");

    addSensor(tempSensor);
    addSensor(humSensor);

    SensorSketch::setup();
}

void LAFVIN_R3_CH340_DHT11_Sketch::loop() {
    SensorSketch::loop();
}