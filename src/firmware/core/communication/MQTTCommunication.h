// src/firmware/core/communication/MQTTCommunication.h
#ifndef MQTT_COMMUNICATION_H
#define MQTT_COMMUNICATION_H

#include "ICommunication.h"
#include <PubSubClient.h>

#ifdef ARDUINO
#include <Arduino.h>
#include <avr/wdt.h>
#else
#include "ArduinoMock.h"
#define wdt_reset()
#endif

class MQTTCommunication : public ICommunication {
private:
    Client& _networkClient;
    PubSubClient _pubSub;
    const char* _brokerIP;
    uint16_t _brokerPort;
    const char* _parcelaId;

    char _topicSensores[48];
    char _topicEstado[48];
    char _topicControl[48];
    char _clientId[32];

    static MQTTCommunication* _instance;
    static void onMessage(char* topic, uint8_t* payload, unsigned int length);

    // Buffer circular para simular read() desde callback MQTT
    static constexpr uint16_t INPUT_BUFFER_SIZE = 256;
    char _inputBuffer[INPUT_BUFFER_SIZE];
    uint16_t _inputHead;
    uint16_t _inputTail;
    bool _inputOverflow;

    void appendToBuffer(char c);
    void buildTopics();

public:
    MQTTCommunication(Client& networkClient,
                      const char* brokerIP,
                      uint16_t brokerPort,
                      const char* parcelaId);

    void begin() override;
    bool available() override;
    int read() override;
    void send(const char* data) override;
    void send(const uint8_t* data, uint16_t len) override;
    bool connected() override;
    void loop() override;
    const char* name() const override { return "mqtt"; }

    // MQTT específico
    bool connect();
    void subscribe(const char* topic);
    void publishSensorData(float humSuelo, float humAire, float temp, uint32_t uptime);
    void publishState(const char* stateName, bool relayOn, uint32_t uptime);
};

#endif