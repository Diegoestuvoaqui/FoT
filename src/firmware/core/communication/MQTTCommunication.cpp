// src/firmware/core/communication/MQTTCommunication.cpp
#include "MQTTCommunication.h"
#include <string.h>
#include <stdlib.h>

MQTTCommunication* MQTTCommunication::_instance = nullptr;

MQTTCommunication::MQTTCommunication(Client& networkClient,
                                     const char* brokerIP,
                                     uint16_t brokerPort,
                                     const char* parcelaId)
    : _networkClient(networkClient)
    , _pubSub(networkClient)
    , _brokerIP(brokerIP)
    , _brokerPort(brokerPort)
    , _parcelaId(parcelaId)
    , _inputHead(0)
    , _inputTail(0)
    , _inputOverflow(false) {
    buildTopics();
    _instance = this;
}

void MQTTCommunication::buildTopics() {
    snprintf(_topicSensores, sizeof(_topicSensores), "fot/%s/sensores", _parcelaId);
    snprintf(_topicEstado, sizeof(_topicEstado), "fot/%s/estado", _parcelaId);
    snprintf(_topicControl, sizeof(_topicControl), "fot/%s/control", _parcelaId);
    snprintf(_clientId, sizeof(_clientId), "fot-%s", _parcelaId);
}

void MQTTCommunication::begin() {
    _pubSub.setServer(_brokerIP, _brokerPort);
    _pubSub.setCallback(onMessage);
    _pubSub.setBufferSize(256);
}

bool MQTTCommunication::connect() {
    for (uint8_t i = 0; i < 3; i++) {
        wdt_reset();
        if (_pubSub.connect(_clientId)) {
            _pubSub.subscribe(_topicControl, 1);
            return true;
        }
        delay(1000);
    }
    return false;
}

bool MQTTCommunication::connected() {
    return _pubSub.connected();
}

void MQTTCommunication::loop() {
    if (!_pubSub.connected()) {
        connect();
    }
    _pubSub.loop();
}

bool MQTTCommunication::available() {
    return _inputHead != _inputTail;
}

int MQTTCommunication::read() {
    if (_inputHead == _inputTail) {
        return -1;
    }
    char c = _inputBuffer[_inputTail];
    _inputTail = (_inputTail + 1) % INPUT_BUFFER_SIZE;
    return (int)(uint8_t)c;
}

void MQTTCommunication::send(const char* data) {
    _pubSub.publish(_topicSensores, data, false);
}

void MQTTCommunication::send(const uint8_t* data, uint16_t len) {
    _pubSub.publish(_topicSensores, data, len, false);
}

void MQTTCommunication::subscribe(const char* topic) {
    _pubSub.subscribe(topic);
}

void MQTTCommunication::publishSensorData(float humSuelo, float humAire, float temp, uint32_t uptime) {
    char buf[128];
    snprintf(buf, sizeof(buf),
             "{\"hum_suelo\":%.1f,\"hum_aire\":%.1f,\"temp\":%.1f,\"ts\":%lu}",
             humSuelo, humAire, temp, uptime);
    _pubSub.publish(_topicSensores, buf, false);
}

void MQTTCommunication::publishState(const char* stateName, bool relayOn, uint32_t uptime) {
    char buf[96];
    snprintf(buf, sizeof(buf),
             "{\"state\":\"%s\",\"relay\":%s,\"uptime\":%lu}",
             stateName,
             relayOn ? "true" : "false",
             uptime);
    _pubSub.publish(_topicEstado, buf, false);
}

void MQTTCommunication::appendToBuffer(char c) {
    uint16_t nextHead = (_inputHead + 1) % INPUT_BUFFER_SIZE;
    if (nextHead == _inputTail) {
        _inputOverflow = true;
        return;
    }
    _inputBuffer[_inputHead] = c;
    _inputHead = nextHead;
}

void MQTTCommunication::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    if (!_instance) return;

    // Solo procesamos mensajes del topic de control
    if (strncmp(topic, _instance->_topicControl,
                strlen(_instance->_topicControl)) != 0) {
        return;
    }

    // Copiar payload al buffer circular para que read() lo consuma
    for (unsigned int i = 0; i < length && i < 255; i++) {
        _instance->appendToBuffer((char)payload[i]);
    }
    _instance->appendToBuffer('\n');
}