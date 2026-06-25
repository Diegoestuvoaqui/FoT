#ifndef STATEMACHINE_H
#define STATEMACHINE_H

#include "IState.h"
#include "ISensor.h"
#include "SensorType.h"

#ifdef ARDUINO
#include <Arduino.h>
#else
#include "ArduinoMock.h"
#endif

#include "../persistence/EEPROMConfig.h"

#define MAX_SENSORS 4

// Pines del relé (ajústalos a tu hardware)
#ifndef RELAY_PIN
#define RELAY_PIN   5
#endif
#ifndef RELAY_ON
#define RELAY_ON    LOW
#endif
#ifndef RELAY_OFF
#define RELAY_OFF   HIGH
#endif

class StateMachine {
private:
    IState *currentState;

    ISensor *sensors[MAX_SENSORS];
    uint8_t sensorCount;

    bool _startInAutoMode;

    // Últimas lecturas
    float humiditySoil;
    float humidityAir;
    float temperature;

    // Umbrales y configuración
    float thresholdMin;
    float thresholdMax;
    uint32_t irrigationTimeout; // segundos
    ConfigData _config; // config activa cargada desde EEPROM

    // Comando pendiente (desde MQTT)
    const char *pendingCmd;

    // Seguimiento de fallos por sensor
    uint8_t invalidCounts[MAX_SENSORS];
    bool sensorFaultFlag; // true si algún sensor llegó a 3 fallos consecutivos

    // Métodos internos
    void setRelay(bool on);

    void checkSensorFault();

public:
    StateMachine();

    ~StateMachine();

    void addSensor(ISensor *sensor);

    void updateSensors();

    // Lecturas
    float getHumidity() const;

    float getHumidityAir() const;

    float getTemperature() const;

    // Umbrales
    float getThresholdMin() const;

    float getThresholdMax() const;

    void updateThresholds(float min, float max);

    // Sensores enable/disable
    void setSensorEnabled(SensorType type, bool enabled);

    // Relay
    void turnRelayOn();

    void turnRelayOff();
    
    // Startup (desde EEPROM)
    void applyStartupState();

    void setStartInAutoMode(bool v); // actualiza flag y persiste

    // Estado
    void setState(IState *newState);

    void tick();

    // Comandos
    void dispatchCommand(const char *cmd, const char *param1 = nullptr, float val1 = 0.0f, float val2 = 0.0f);

    const char *getPendingCommand() const;

    void clearPendingCommand();

    // Fallo de sensor
    bool hasSensorFault() const;

    void resetSensorFault();

    // Publicación de lecturas (MQTT) — stub, implementar cuando tengas MQTT
    void publishSensorReadings();

    // Timeout de riego
    uint32_t getIrrigationTimeout() const;

    uint8_t getSensorCount() const { return sensorCount; }

    const char *getCurrentStateName() const {
        return currentState ? currentState->name() : "None";
    }
};

#endif
