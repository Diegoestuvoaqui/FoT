// src/firmware/core/communication/WiFiCommunication.cpp
#include "WiFiCommunication.h"
#include <string.h>

WiFiCommunication* WiFiCommunication::_instance = nullptr;

WiFiCommunication::WiFiCommunication(const char* ssid,
                                       const char* password,
                                       const char* brokerIP,
                                       uint16_t brokerPort,
                                       const char* parcelaId)
    : _pubSub(_wifiClient)
    , _ssid(ssid)
    , _password(password)
    , _brokerIP(brokerIP)
    , _brokerPort(brokerPort)
    , _parcelaId(parcelaId)
    , _inputHead(0)
    , _inputTail(0) {
    buildTopics();
    _instance = this;
}

void WiFiCommunication::buildTopics() {
    snprintf(_topicSensores, sizeof(_topicSensores), "fot/%s/sensores", _parcelaId);
    snprintf(_topicControl, sizeof(_topicControl), "fot/%s/control", _parcelaId);
    snprintf(_clientId, sizeof(_clientId), "fot-%s", _parcelaId);
}

void WiFiCommunication::begin() {
    connectWiFi();
    _pubSub.setServer(_brokerIP, _brokerPort);
    _pubSub.setCallback(onMessage);
    _pubSub.setBufferSize(256);
}

bool WiFiCommunication::connectWiFi() {
    WiFi.begin(_ssid, _password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        attempts++;
    }
    return WiFi.status() == WL_CONNECTED;
}

bool WiFiCommunication::connectMQTT() {
    for (uint8_t i = 0; i < 3; i++) {
        if (_pubSub.connect(_clientId)) {
            _pubSub.subscribe(_topicControl, 1);
            return true;
        }
        delay(1000);
    }
    return false;
}

bool WiFiCommunication::connected() {
    return WiFi.status() == WL_CONNECTED && _pubSub.connected();
}

void WiFiCommunication::loop() {
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }
    if (!_pubSub.connected()) {
        connectMQTT();
    }
    _pubSub.loop();
}

bool WiFiCommunication::available() {
    return _inputHead != _inputTail;
}

int WiFiCommunication::read() {
    if (_inputHead == _inputTail) return -1;
    char c = _inputBuffer[_inputTail];
    _inputTail = (_inputTail + 1) % INPUT_BUFFER_SIZE;
    return (int)(uint8_t)c;
}

void WiFiCommunication::send(const char* data) {
    _pubSub.publish(_topicSensores, data, false);
}

void WiFiCommunication::appendToBuffer(char c) {
    uint16_t nextHead = (_inputHead + 1) % INPUT_BUFFER_SIZE;
    if (nextHead == _inputTail) return; // overflow, descartar
    _inputBuffer[_inputHead] = c;
    _inputHead = nextHead;
}

void WiFiCommunication::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    if (!_instance) return;
    if (strncmp(topic, _instance->_topicControl, strlen(_instance->_topicControl)) != 0) return;

    for (unsigned int i = 0; i < length && i < 255; i++) {
        _instance->appendToBuffer((char)payload[i]);
    }
    _instance->appendToBuffer('\n');
}