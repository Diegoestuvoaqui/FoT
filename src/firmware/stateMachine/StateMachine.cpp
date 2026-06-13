#include "StateMachine.h"
#include "StateIdle.h"
#include "StateMonitoring.h"
#include "StateIrrigating.h"
#include "StateFault.h"
#include <string.h>

// --------------------------------------------------------------------------
// Función auxiliar para mapear cadenas de comandos a SensorType
static SensorType sensorTypeFromStr(const char *name) {
    if (strncmp(name, "DHT22_TEMP", 10) == 0) return SENSOR_DHT22_TEMP;
    if (strncmp(name, "DHT22_HUM", 9) == 0) return SENSOR_DHT22_HUM;
    if (strncmp(name, "SOIL_CAP", 8) == 0) return SENSOR_SOIL_CAP;
    return (SensorType) 255; // no reconocido
}

// --------------------------------------------------------------------------
// Constructor / Destructor
StateMachine::StateMachine()
    : currentState(nullptr)
      , sensorCount(0)
      , _startInAutoMode(false)
      , humiditySoil(NAN)
      , humidityAir(NAN)
      , temperature(NAN)
      , thresholdMin(30.0f)
      , thresholdMax(70.0f)
      , irrigationTimeout(300)
      , pendingCmd(nullptr)
      , sensorFaultFlag(false) {
    memset(invalidCounts, 0, sizeof(invalidCounts));
    memset(&_config, 0, sizeof(_config)); // solo RAM — applyStartupState() carga EEPROM
}

StateMachine::~StateMachine() {
    if (currentState) delete currentState;
}

// --------------------------------------------------------------------------
// Configuración de sensores
void StateMachine::addSensor(ISensor *sensor) {
    if (sensorCount < MAX_SENSORS) {
        sensors[sensorCount++] = sensor;
    }
}

void StateMachine::updateSensors() {
    humiditySoil = NAN;
    humidityAir = NAN;
    temperature = NAN;

    for (uint8_t i = 0; i < sensorCount; i++) {
        ISensor *s = sensors[i];
        if (!s->isEnabled()) continue;

        float val = s->read();
        switch (s->getType()) {
            case SENSOR_SOIL_CAP: humiditySoil = val;
                break;
            case SENSOR_DHT22_TEMP: temperature = val;
                break;
            case SENSOR_DHT22_HUM: humidityAir = val;
                break;
        }

        if (s->isValid()) {
            invalidCounts[i] = 0;
        } else {
            if (invalidCounts[i] < 255) invalidCounts[i]++;
        }
    }

    checkSensorFault();
}

void StateMachine::checkSensorFault() {
    sensorFaultFlag = false;
    for (uint8_t i = 0; i < sensorCount; i++) {
        if (sensors[i]->isEnabled() && invalidCounts[i] >= 3) {
            sensorFaultFlag = true;
            break;
        }
    }
}

bool StateMachine::hasSensorFault() const { return sensorFaultFlag; }

void StateMachine::resetSensorFault() {
    memset(invalidCounts, 0, sizeof(invalidCounts));
    sensorFaultFlag = false;
}

// --------------------------------------------------------------------------
// Getters de lecturas
float StateMachine::getHumidity() const { return humiditySoil; }
float StateMachine::getHumidityAir() const { return humidityAir; }
float StateMachine::getTemperature() const { return temperature; }

// --------------------------------------------------------------------------
// Umbrales
float StateMachine::getThresholdMin() const { return thresholdMin; }
float StateMachine::getThresholdMax() const { return thresholdMax; }

void StateMachine::updateThresholds(float min, float max) {
    thresholdMin = min;
    thresholdMax = max;
    _config.humidityThresholdMin = min;
    _config.humidityThresholdMax = max;
    EEPROMConfig::save(_config);
}

// --------------------------------------------------------------------------
// Sensores enable/disable
void StateMachine::setSensorEnabled(SensorType type, bool enabled) {
    for (uint8_t i = 0; i < sensorCount; i++) {
        if (sensors[i]->getType() == type) {
            sensors[i]->setEnabled(enabled);
        }
    }
}

// --------------------------------------------------------------------------
// Relay
void StateMachine::setRelay(bool on) {
    digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF);
}

void StateMachine::turnRelayOn() { setRelay(true); }
void StateMachine::turnRelayOff() { setRelay(false); }

// --------------------------------------------------------------------------
// Arranque desde EEPROM
void StateMachine::applyStartupState() {
    bool ok = EEPROMConfig::load(_config);
    if (!ok) {
        Serial.println("EEPROM: checksum invalido, se cargaron valores por defecto");
    }

    thresholdMin = _config.humidityThresholdMin;
    thresholdMax = _config.humidityThresholdMax;
    irrigationTimeout = _config.irrigationTimeoutSec;
    _startInAutoMode = _config.startInAutoMode;

    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, RELAY_OFF); // garantía: relay apagado al arrancar

    if (_config.startInAutoMode) setState(new StateMonitoring());
    else setState(new StateIdle());
}

void StateMachine::setStartInAutoMode(bool v) {
    _startInAutoMode = v;
    _config.startInAutoMode = v ? 1 : 0;
    EEPROMConfig::save(_config);
}

// --------------------------------------------------------------------------
// Cambio de estado
void StateMachine::setState(IState *newState) {
    if (currentState) delete currentState;
    currentState = newState;
}

void StateMachine::tick() {
    if (currentState) currentState->handle(*this);
}

// --------------------------------------------------------------------------
// Despacho de comandos MQTT
void StateMachine::dispatchCommand(const char *cmd, const char *param1,
                                   float val1, float val2) {
    if (strncmp(cmd, "enable_sensor", 13) == 0) {
        SensorType t = sensorTypeFromStr(param1);
        if ((uint8_t) t != 255) setSensorEnabled(t, true);
        return;
    }
    if (strncmp(cmd, "disable_sensor", 14) == 0) {
        SensorType t = sensorTypeFromStr(param1);
        if ((uint8_t) t != 255) setSensorEnabled(t, false);
        return;
    }
    if (strncmp(cmd, "set_thresholds", 14) == 0) {
        updateThresholds(val1, val2);
        return;
    }

    pendingCmd = cmd;
}

const char *StateMachine::getPendingCommand() const { return pendingCmd; }
void StateMachine::clearPendingCommand() { pendingCmd = nullptr; }

// --------------------------------------------------------------------------
// Publicación de lecturas (stub — TODO: integrar con MQTTClient)
void StateMachine::publishSensorReadings() {
    Serial.print("Suelo:");
    Serial.print(humiditySoil);
    Serial.print(" Aire:");
    Serial.print(humidityAir);
    Serial.print(" Temp:");
    Serial.println(temperature);
}

// --------------------------------------------------------------------------
uint32_t StateMachine::getIrrigationTimeout() const { return irrigationTimeout; }
