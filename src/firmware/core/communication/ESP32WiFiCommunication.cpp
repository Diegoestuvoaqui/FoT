// src/firmware/core/communication/ESP32WiFiCommunication.cpp
#include "ESP32WiFiCommunication.h"

#if defined(ARDUINO_ARCH_ESP32)
#include <string.h>

ESP32WiFiCommunication* ESP32WiFiCommunication::_instance = nullptr;

ESP32WiFiCommunication::ESP32WiFiCommunication(const char* ssid,
                                               const char* password,
                                               const char* brokerFallbackIP,
                                               uint16_t brokerFallbackPort,
                                               const char* boardId)
    : _pubSub(_wifiClient)
    , _ssid(ssid)
    , _password(password)
    , _fallbackIP(brokerFallbackIP)
    , _fallbackPort(brokerFallbackPort)
    , _brokerPort(brokerFallbackPort)
    , _boardId(boardId)
    , _lastWifiAttempt(0)
    , _lastMqttAttempt(0)
    , _wifiBackoff(1000)
    , _mqttBackoff(1000)
    , _resolveNeeded(true)
    , _inputHead(0)
    , _inputTail(0) {
    buildTopics();
    _instance = this;
}

void ESP32WiFiCommunication::buildTopics() {
    snprintf(_topicSensores, sizeof(_topicSensores), "fot/%s/sensores", _boardId);
    snprintf(_topicEstado, sizeof(_topicEstado), "fot/%s/estado", _boardId);
    snprintf(_topicControl, sizeof(_topicControl), "fot/%s/control", _boardId);
    snprintf(_clientId, sizeof(_clientId), "%s", _boardId);
}

void ESP32WiFiCommunication::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(false);
    WiFi.begin(_ssid, _password);

    _pubSub.setCallback(onMessage);
    _pubSub.setBufferSize(512);
}

bool ESP32WiFiCommunication::resolveBroker() {
    if (MDNS.begin(_clientId)) {
        int n = MDNS.queryService("mqtt", "tcp");
        for (int i = 0; i < n; i++) {
            if (MDNS.port(i) != 0) {
                _brokerIP = MDNS.IP(i);
                _brokerPort = MDNS.port(i);
                MDNS.end();
                return true;
            }
        }
        MDNS.end();
    }
    _brokerIP.fromString(_fallbackIP);
    _brokerPort = _fallbackPort;
    return false;
}

bool ESP32WiFiCommunication::connectMQTT() {
    bool ok = _pubSub.connect(_clientId,
                              nullptr, nullptr,
                              _topicEstado, 1, true, "{\"status\":\"offline\"}");
    if (!ok) {
        return false;
    }

    _pubSub.subscribe(_topicControl, 1);

    IPAddress ip = WiFi.localIP();
    uint64_t mac = ESP.getEfuseMac();
    char buf[192];
    snprintf(buf, sizeof(buf),
             "{\"status\":\"online\",\"boot\":true,\"hw\":\"esp32\","
             "\"mac\":\"%04X%08X\",\"ip\":\"%d.%d.%d.%d\",\"rssi\":%d}",
             (unsigned int)(mac >> 32), (unsigned int)(mac & 0xFFFFFFFFUL),
             ip[0], ip[1], ip[2], ip[3],
             WiFi.RSSI());
    _pubSub.publish(_topicEstado, buf, false);
    return true;
}

bool ESP32WiFiCommunication::connected() {
    return WiFi.status() == WL_CONNECTED && _pubSub.connected();
}

void ESP32WiFiCommunication::loop() {
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED) {
        if (_pubSub.connected()) _pubSub.disconnect();
        if (now - _lastWifiAttempt >= _wifiBackoff) {
            _lastWifiAttempt = now;
            _wifiBackoff = min(_wifiBackoff * 2, 30000UL);
            WiFi.disconnect();
            WiFi.begin(_ssid, _password);
        }
        return;
    }
    _wifiBackoff = 1000;

    if (!_pubSub.connected()) {
        if (now - _lastMqttAttempt >= _mqttBackoff) {
            _lastMqttAttempt = now;
            _mqttBackoff = min(_mqttBackoff * 2, 30000UL);
            if (_resolveNeeded) {
                resolveBroker();
                _resolveNeeded = false;
            }
            _pubSub.setServer(_brokerIP, _brokerPort);
            if (connectMQTT()) {
                _mqttBackoff = 1000;
            }
        }
        return;
    }

    _pubSub.loop();
}

bool ESP32WiFiCommunication::available() {
    return _inputHead != _inputTail;
}

int ESP32WiFiCommunication::read() {
    if (_inputHead == _inputTail) return -1;
    char c = _inputBuffer[_inputTail];
    _inputTail = (_inputTail + 1) % INPUT_BUFFER_SIZE;
    return (int)(uint8_t)c;
}

void ESP32WiFiCommunication::send(const char* data) {
    _pubSub.publish(_topicSensores, data, false);
}

void ESP32WiFiCommunication::sendStatus(const char* data) {
    _pubSub.publish(_topicEstado, data, false);
}

void ESP32WiFiCommunication::appendToBuffer(char c) {
    uint16_t nextHead = (_inputHead + 1) % INPUT_BUFFER_SIZE;
    if (nextHead == _inputTail) return;
    _inputBuffer[_inputHead] = c;
    _inputHead = nextHead;
}

void ESP32WiFiCommunication::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    if (!_instance) return;

    size_t topicControlLen = strlen(_instance->_topicControl);
    if (strlen(topic) != topicControlLen ||
        strncmp(topic, _instance->_topicControl, topicControlLen) != 0) {
        return;
    }

    for (unsigned int i = 0; i < length && i < 255; i++) {
        _instance->appendToBuffer((char)payload[i]);
    }
    _instance->appendToBuffer('\n');
}

#endif