// src/firmware/core/communication/ESP32WiFiCommunication.h
#ifndef ESP32_WIFI_COMMUNICATION_H
#define ESP32_WIFI_COMMUNICATION_H

#if defined(ARDUINO_ARCH_ESP32)

#include "ICommunication.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <PubSubClient.h>

class ESP32WiFiCommunication : public ICommunication {
private:
    WiFiClient _wifiClient;
    PubSubClient _pubSub;
    const char* _ssid;
    const char* _password;
    const char* _fallbackIP;
    uint16_t _fallbackPort;
    IPAddress _brokerIP;
    uint16_t _brokerPort;
    const char* _boardId;

    char _topicSensores[48];
    char _topicEstado[48];
    char _topicControl[48];
    char _clientId[32];

    unsigned long _lastWifiAttempt;
    unsigned long _lastMqttAttempt;
    unsigned long _wifiBackoff;
    unsigned long _mqttBackoff;
    bool _resolveNeeded;

    static ESP32WiFiCommunication* _instance;
    static void onMessage(char* topic, uint8_t* payload, unsigned int length);

    static constexpr uint16_t INPUT_BUFFER_SIZE = 256;
    char _inputBuffer[INPUT_BUFFER_SIZE];
    uint16_t _inputHead;
    uint16_t _inputTail;

    void appendToBuffer(char c);
    void buildTopics();
    bool resolveBroker();

public:
    ESP32WiFiCommunication(const char* ssid,
                           const char* password,
                           const char* brokerFallbackIP,
                           uint16_t brokerFallbackPort,
                           const char* boardId);

    void begin() override;
    bool available() override;
    int read() override;
    void send(const char* data) override;
    void sendStatus(const char* data) override;
    bool connected() override;
    void loop() override;
    const char* name() const override { return "esp32-wifi"; }

    bool connectMQTT();
};

#endif
#endif