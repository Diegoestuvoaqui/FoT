// src/firmware/core/communication/WiFiCommunication.h
#ifndef WIFI_COMMUNICATION_H
#define WIFI_COMMUNICATION_H

#include "ICommunication.h"
#include <WiFiS3.h>        // Librería WiFi del UNO R4 WiFi
#include <PubSubClient.h>

class WiFiCommunication : public ICommunication {
private:
    WiFiClient _wifiClient;
    PubSubClient _pubSub;
    const char* _ssid;
    const char* _password;
    const char* _brokerIP;
    uint16_t _brokerPort;
    const char* _parcelaId;

    char _topicSensores[48];
    char _topicControl[48];
    char _clientId[32];

    static WiFiCommunication* _instance;
    static void onMessage(char* topic, uint8_t* payload, unsigned int length);

    static constexpr uint16_t INPUT_BUFFER_SIZE = 256;
    char _inputBuffer[INPUT_BUFFER_SIZE];
    uint16_t _inputHead;
    uint16_t _inputTail;

    void appendToBuffer(char c);
    void buildTopics();

public:
    WiFiCommunication(const char* ssid,
                      const char* password,
                      const char* brokerIP,
                      uint16_t brokerPort,
                      const char* parcelaId);

    void begin() override;
    bool available() override;
    int read() override;
    void send(const char* data) override;
    bool connected() override;
    void loop() override;
    const char* name() const override { return "wifi"; }

    // WiFi específico
    bool connectWiFi();
    bool connectMQTT();
};

#endif