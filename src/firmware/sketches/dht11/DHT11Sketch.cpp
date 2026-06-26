// src/firmware/sketches/dht11/DHT11Sketch.cpp
#include "DHT11Sketch.h"
#include "../../abstractSensors/SensorFactory.h"
#include "../../stateMachine/StateIdle.h"
#include "../../stateMachine/StateMonitoring.h"
#include "../../stateMachine/StateIrrigating.h"
#include "../../stateMachine/StateFault.h"
#include <string.h>

DHT11Sketch::DHT11Sketch()
    : currentState(nullptr)
    , sensorCount(0)
    , _startInAutoMode(false)
    , humiditySoil(NAN)
    , humidityAir(NAN)
    , temperature(NAN)
    , thresholdMin(30.0f)
    , thresholdMax(70.0f)
    , irrigationTimeout(300)
    , sensorFaultFlag(false) {
    memset(invalidCounts, 0, sizeof(invalidCounts));
    memset(&_config, 0, sizeof(_config));
}

DHT11Sketch::~DHT11Sketch() {
    if (currentState) delete currentState;
}

void DHT11Sketch::setup() {
    send("DHT11Sketch::setup()");

    // Cargar configuración desde EEPROM
    bool ok = EEPROMConfig::load(_config);
    if (!ok) {
        Serial.println(F("EEPROM: checksum invalido, se cargaron valores por defecto"));
        EEPROMConfig::writeDefaults(_config);
    }

    thresholdMin = _config.humidityThresholdMin;
    thresholdMax = _config.humidityThresholdMax;
    irrigationTimeout = _config.irrigationTimeoutSec;
    _startInAutoMode = _config.startInAutoMode;

    // Configurar pin de relé
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, RELAY_OFF);

    // Crear sensores por defecto
    ISensor* tempSensor = SensorFactory::create(SENSOR_DHT11_TEMP, 2);
    ISensor* humSensor = SensorFactory::create(SENSOR_DHT11_HUM, 2);

    if (tempSensor) addSensor(tempSensor);
    else Serial.println(F("ERROR: sensor temperatura no creado"));

    if (humSensor) addSensor(humSensor);
    else Serial.println(F("ERROR: sensor humedad aire no creado"));

    // Estado inicial
    if (_config.startInAutoMode) {
        setState(new StateMonitoring());
    } else {
        setState(new StateIdle());
    }

    Serial.print(F("Estado inicial: "));
    Serial.println(getCurrentStateName());
}

void DHT11Sketch::loop() {
    if (currentState) {
        currentState->handle(*this);
    }
}

// ─── Comandos ───────────────────────────────────────────────────────────────

void DHT11Sketch::turnRelayOn() {
    setRelay(true);
}

void DHT11Sketch::turnRelayOff() {
    setRelay(false);
}

void DHT11Sketch::setModeAuto() {
    setStartInAutoMode(true);
    setState(new StateMonitoring());
}

void DHT11Sketch::setModeManual() {
    setStartInAutoMode(false);
    setState(new StateIdle());
}

void DHT11Sketch::resetFault() {
    resetSensorFault();
    setState(new StateIdle());
}

void DHT11Sketch::setThresholds(float min, float max) {
    thresholdMin = min;
    thresholdMax = max;
    _config.humidityThresholdMin = min;
    _config.humidityThresholdMax = max;
    EEPROMConfig::save(_config);
}

void DHT11Sketch::enableSensor(const char* sensorName) {
    SensorType t = sensorTypeFromStr(sensorName);
    if ((uint8_t)t != 255) setSensorEnabled(t, true);
}

void DHT11Sketch::disableSensor(const char* sensorName) {
    SensorType t = sensorTypeFromStr(sensorName);
    if ((uint8_t)t != 255) setSensorEnabled(t, false);
}

// ─── Sensores ─────────────────────────────────────────────────────────────

void DHT11Sketch::addSensor(ISensor* sensor) {
    if (sensorCount < MAX_SENSORS) {
        sensors[sensorCount++] = sensor;
    }
}

void DHT11Sketch::updateSensors() {
    humiditySoil = NAN;
    humidityAir = NAN;
    temperature = NAN;

    for (uint8_t i = 0; i < sensorCount; i++) {
        ISensor* s = sensors[i];
        if (!s->isEnabled()) continue;

        float val = s->read();
        switch (s->getType()) {
            case SENSOR_SOIL_CAP: humiditySoil = val; break;
            case SENSOR_DHT11_TEMP: temperature = val; break;
            case SENSOR_DHT11_HUM: humidityAir = val; break;
        }

        if (s->isValid()) {
            invalidCounts[i] = 0;
        } else {
            if (invalidCounts[i] < 255) invalidCounts[i]++;
        }
    }

    checkSensorFault();
}

void DHT11Sketch::checkSensorFault() {
    sensorFaultFlag = false;
    for (uint8_t i = 0; i < sensorCount; i++) {
        if (sensors[i]->isEnabled() && invalidCounts[i] >= 3) {
            sensorFaultFlag = true;
            break;
        }
    }
}

void DHT11Sketch::resetSensorFault() {
    memset(invalidCounts, 0, sizeof(invalidCounts));
    sensorFaultFlag = false;
}

void DHT11Sketch::setSensorEnabled(SensorType type, bool enabled) {
    for (uint8_t i = 0; i < sensorCount; i++) {
        if (sensors[i]->getType() == type) {
            sensors[i]->setEnabled(enabled);
        }
    }
}

SensorType DHT11Sketch::sensorTypeFromStr(const char* name) {
    if (strncmp(name, "DHT11_TEMP", 10) == 0) return SENSOR_DHT11_TEMP;
    if (strncmp(name, "DHT11_HUM", 9) == 0) return SENSOR_DHT11_HUM;
    if (strncmp(name, "SOIL_CAP", 8) == 0) return SENSOR_SOIL_CAP;
    return (SensorType)255;
}

// ─── Relay ──────────────────────────────────────────────────────────────────

void DHT11Sketch::setRelay(bool on) {
    digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF);
}

// ─── Estado ─────────────────────────────────────────────────────────────────

void DHT11Sketch::setState(IState* newState) {
    if (currentState) delete currentState;
    currentState = newState;
}

const char* DHT11Sketch::getCurrentStateName() const {
    return currentState ? currentState->name() : "None";
}

// ─── Configuración ──────────────────────────────────────────────────────────

void DHT11Sketch::setStartInAutoMode(bool v) {
    _startInAutoMode = v;
    _config.startInAutoMode = v ? 1 : 0;
    EEPROMConfig::save(_config);
}

// ─── Publicación de lecturas ───────────────────────────────────────────────

void DHT11Sketch::publishSensorReadings() {
    char buf[160];
    char airStr[8], tempStr[8];

    dtostrf(isnan(humidityAir) ? 0.0f : humidityAir, 4, 1, airStr);
    dtostrf(isnan(temperature) ? 0.0f : temperature, 4, 1, tempStr);

    const char* stName = getCurrentStateName();

    if (isnan(humiditySoil)) {
        snprintf(buf, sizeof(buf),
            "{\"hum_suelo\":null,\"hum_aire\":%s,\"temp\":%s,\"relay\":%d,\"state\":\"%s\"}",
            airStr, tempStr,
            digitalRead(RELAY_PIN) == RELAY_ON ? 1 : 0,
            stName);
    } else {
        char soilStr[8];
        dtostrf(humiditySoil, 4, 1, soilStr);
        snprintf(buf, sizeof(buf),
            "{\"hum_suelo\":%s,\"hum_aire\":%s,\"temp\":%s,\"relay\":%d,\"state\":\"%s\"}",
            soilStr, airStr, tempStr,
            digitalRead(RELAY_PIN) == RELAY_ON ? 1 : 0,
            stName);
    }

    // Usar Bridge en lugar de Serial directo
    send(buf);
}