// src/main.cpp
#ifdef ARDUINO
#include <Arduino.h>
#include <Ethernet.h>
#include <avr/wdt.h>
#else
#include "ArduinoMock.h"
#endif

#include "firmware/abstractSensors/SensorFactory.h"
#include "firmware/stateMachine/StateMachine.h"
#include "firmware/connection/MQTTClient.h"

StateMachine fsm;

#ifdef ARDUINO
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x01};
EthernetClient ethClient;
MQTTClient mqtt(ethClient, "192.168.1.100", 1883, "p1");
#endif

void setup() {
    Serial.begin(9600);

    ISensor *soil = SensorFactory::create(SENSOR_SOIL_CAP, A0, 800, 300);
    ISensor *temp = SensorFactory::create(SENSOR_DHT22_TEMP, 2);
    ISensor *hum = SensorFactory::create(SENSOR_DHT22_HUM, 2);

    if (soil) fsm.addSensor(soil);
    else Serial.println("ERROR: sensor suelo no creado");

    if (temp) fsm.addSensor(temp);
    else Serial.println("ERROR: sensor temperatura no creado");

    if (hum) fsm.addSensor(hum);
    else Serial.println("ERROR: sensor humedad aire no creado");

    fsm.applyStartupState();

#ifdef ARDUINO
    Ethernet.begin(mac);
    delay(1500);
    mqtt.begin(&fsm);
    if (!mqtt.connect()) {
        Serial.println("MQTT: sin conexion al arrancar, reintentando en loop");
    }
    wdt_enable(WDTO_8S); // watchdog al final, cuando todo está listo
#endif
}

void loop() {
#ifdef ARDUINO
    mqtt.loop();
#endif
    fsm.tick();
    delay(500);
#ifdef ARDUINO
    wdt_reset();
#endif
}
