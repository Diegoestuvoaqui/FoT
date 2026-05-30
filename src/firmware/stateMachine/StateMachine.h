#ifndef STATEMACHINE_H
#define STATEMACHINE_H

#include "IState.h"
#include "ISensor.h"
#include "SensorType.h"
// Después:
#ifdef ARDUINO
  #include <Arduino.h>
#else
  #include "ArduinoMock.h"
#endif

#define MAX_SENSORS 4

// Placeholder: estructura de configuración (debe coincidir con EEPROMConfig)
struct ConfigData {
    uint8_t startInAutoMode;
    float threshold_min;
    float threshold_max;
    uint32_t irrigationTimeout; // en segundos
};

// Pines del relé (ajústalos a tu hardware)
#ifndef RELAY_PIN
#define RELAY_PIN   5
#endif
#ifndef RELAY_ON
#define RELAY_ON    HIGH
#endif
#ifndef RELAY_OFF
#define RELAY_OFF   LOW
#endif

class StateMachine {
private:
    IState* currentState;

    ISensor* sensors[MAX_SENSORS];
    uint8_t sensorCount;

    // Últimas lecturas
    float humiditySoil;
    float humidityAir;
    float temperature;

    // Umbrales y configuración
    float thresholdMin;
    float thresholdMax;
    uint32_t irrigationTimeout; // segundos

    // Autenticación del Farmer
    bool farmerAuthenticated;

    // Comando pendiente (desde MQTT)
    const char* pendingCmd;

    // Seguimiento de fallos por sensor
    uint8_t invalidCounts[MAX_SENSORS];
    bool sensorFaultFlag;  // true si algún sensor llegó a 3 fallos consecutivos

    // Métodos internos
    void setRelay(bool on);
    void checkSensorFault();   // actualiza sensorFaultFlag según invalidCounts

public:
    StateMachine();
    ~StateMachine();

    void addSensor(ISensor* sensor);
    void updateSensors();

    // Lecturas
    float getHumidity() const;      // suelo
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

    // Autenticación
    bool isFarmerAuthenticated() const;
    void setFarmerAuthenticated(bool v);

    // Startup (desde EEPROM)
    void applyStartupState();
    void setStartInAutoMode(bool v); // actualiza flag y persiste

    // Estado
    void setState(IState* newState);
    void tick();

    // Comandos
    void dispatchCommand(const char* cmd, const char* param1 = nullptr, float val1 = 0.0f, float val2 = 0.0f);
    const char* getPendingCommand() const;
    void clearPendingCommand();

    // Fallo de sensor
    bool hasSensorFault() const;
    void resetSensorFault();

    // Publicación de lecturas (MQTT) – stub, implementar cuando tengas MQTT
    void publishSensorReadings();

    // Timeout de riego
    uint32_t getIrrigationTimeout() const;

    // Acceso al número de sensores (útil para los estados)
    uint8_t getSensorCount() const { return sensorCount; }

    const char* getCurrentStateName() const {
    return currentState ? currentState->name() : "None";
}
};

#endif