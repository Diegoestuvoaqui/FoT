#include "MQTTClient.h"
#include "../stateMachine/StateMachine.h"
#include <string.h>
#include <stdlib.h>   // atof()

// Definición del puntero estático
MQTTClient *MQTTClient::_instance = nullptr;

// --------------------------------------------------------------------------
// Constructor — construye los tópicos una sola vez en SRAM
MQTTClient::MQTTClient(Client &networkClient,
                       const char *brokerIP,
                       uint16_t brokerPort,
                       const char *parcelaId)
    : _pubSub(networkClient)
      , _brokerIP(brokerIP)
      , _brokerPort(brokerPort)
      , _fsm(nullptr) {
    snprintf(_topicSensores, sizeof(_topicSensores), "fot/%s/sensores", parcelaId);
    snprintf(_topicEstado, sizeof(_topicEstado), "fot/%s/estado", parcelaId);
    snprintf(_topicControl, sizeof(_topicControl), "fot/%s/control", parcelaId);
    snprintf(_clientId, sizeof(_clientId), "fot-%s", parcelaId);

    _instance = this;
}

// --------------------------------------------------------------------------
void MQTTClient::begin(StateMachine *fsm) {
    _fsm = fsm;
    _pubSub.setServer(_brokerIP, _brokerPort);
    _pubSub.setCallback(onMessage);
    _pubSub.setBufferSize(256);
}

// --------------------------------------------------------------------------
bool MQTTClient::connect() {
    for (uint8_t i = 0; i < 3; i++) {
        wdt_reset(); // evitar disparo del watchdog
        if (_pubSub.connect(_clientId)) {
            _pubSub.subscribe(_topicControl, 1); // QoS 1
            return true;
        }
        delay(1000); // reducido de 2000 ms a 1000 ms
    }
    return false;
}

// --------------------------------------------------------------------------
void MQTTClient::loop() {
    if (!_pubSub.connected()) {
        connect();
    }
    _pubSub.loop();
}

// --------------------------------------------------------------------------
void MQTTClient::publishSensorData(float humSuelo, float humAire, float temp, uint32_t uptime) {
    char buf[128];
    snprintf(buf, sizeof(buf),
             "{\"hum_suelo\":%.1f,\"hum_aire\":%.1f,\"temp\":%.1f,\"ts\":%lu}",
             humSuelo, humAire, temp, uptime);
    _pubSub.publish(_topicSensores, buf, false);
}

// --------------------------------------------------------------------------
void MQTTClient::publishState(const char *stateName, bool relayOn, uint32_t uptime) {
    char buf[96];
    snprintf(buf, sizeof(buf),
             "{\"state\":\"%s\",\"relay\":%s,\"uptime\":%lu}",
             stateName,
             relayOn ? "true" : "false",
             uptime);
    _pubSub.publish(_topicEstado, buf, false);
}

// --------------------------------------------------------------------------
// Callback estático — ejecutado por PubSubClient al llegar un mensaje
void MQTTClient::onMessage(char *topic, byte *payload, unsigned int length) {
    if (!_instance || !_instance->_fsm) return;

    // Copiar payload a buffer terminado en '\0'
    char msg[64];
    uint8_t len = (length < 63) ? (uint8_t) length : 63;
    memcpy(msg, payload, len);
    msg[len] = '\0';

    // Localizar el campo "cmd"
    char *p = strstr(msg, "\"cmd\"");
    if (!p) return;
    p = strchr(p, ':');
    if (!p) return;
    p++;
    while (*p == ' ' || *p == '"') p++; // saltar espacios y comilla de apertura
    if (*p == '\0') return;

    StateMachine *fsm = _instance->_fsm;

    // ---------- comandos sin parámetros ----------
    if (strncmp(p, "irrigate", 8) == 0) {
        fsm->dispatchCommand("irrigate");
    } else if (strncmp(p, "stop", 4) == 0) {
        fsm->dispatchCommand("stop");
    } else if (strncmp(p, "reset_fault", 11) == 0) {
        fsm->dispatchCommand("reset_fault");
    } else if (strncmp(p, "set_mode_auto", 13) == 0) {
        fsm->dispatchCommand("set_mode_auto");
    } else if (strncmp(p, "set_mode_manual", 15) == 0) {
        fsm->dispatchCommand("set_mode_manual");
    }

    // ---------- set_thresholds: extraer min y max ----------
    else if (strncmp(p, "set_thresholds", 14) == 0) {
        float minVal = 0.0f, maxVal = 0.0f;
        char *q;

        q = strstr(msg, "\"min\":");
        if (q) minVal = atof(q + 6);

        q = strstr(msg, "\"max\":");
        if (q) maxVal = atof(q + 6);

        fsm->dispatchCommand("set_thresholds", nullptr, minVal, maxVal);
    }

    // ---------- enable/disable sensor: extraer nombre ----------
    else if (strncmp(p, "enable_sensor", 13) == 0 ||
             strncmp(p, "disable_sensor", 14) == 0) {
        bool enable = (p[0] == 'e');

        char sensor[16] = {0};
        char *q = strstr(msg, "\"sensor\":"); // busca "sensor": como clave
        if (q) {
            q += 9; // salta los 9 chars de "sensor":
            while (*q == ' ' || *q == '"') q++; // salta espacios y comilla
            uint8_t i = 0;
            while (*q && *q != '"' && i < 15) sensor[i++] = *q++;
            sensor[i] = '\0';
        }

        fsm->dispatchCommand(enable ? "enable_sensor" : "disable_sensor", sensor);
    }
}
