#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <PubSubClient.h>

#ifdef ARDUINO
#include <Arduino.h>
#include <avr/wdt.h>
#else
#include "ArduinoMock.h"
#define wdt_reset()  // no-op fuera de Arduino
#endif

class StateMachine; // forward declaration — evita dependencia circular

class MQTTClient {
public:
    MQTTClient(Client &networkClient,
               const char *brokerIP,
               uint16_t brokerPort,
               const char *parcelaId);

    void begin(StateMachine *fsm); // registra callback y configura servidor
    bool connect(); // hasta 3 intentos con wdt_reset
    void loop(); // mantiene conexión y procesa mensajes
    void publishSensorData(float humSuelo, float humAire, float temp, uint32_t uptime);

    void publishState(const char *stateName, bool relayOn, uint32_t uptime);

private:
    PubSubClient _pubSub;
    const char *_brokerIP;
    uint16_t _brokerPort;
    StateMachine *_fsm;

    // Tópicos construidos en el constructor a partir de parcelaId
    char _topicSensores[48];
    char _topicEstado[48];
    char _topicControl[48];
    char _clientId[32];

    // Callback estático — PubSubClient requiere puntero a función libre
    static MQTTClient *_instance;

    static void onMessage(char *topic, byte *payload, unsigned int length);
};

#endif
