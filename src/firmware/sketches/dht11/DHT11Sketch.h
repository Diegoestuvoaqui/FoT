// src/firmware/sketches/dht11/DHT11Sketch.h
#ifndef DHT11_SKETCH_H
#define DHT11_SKETCH_H

#include "../../core/sketches/SketchBase.h"
#include "../../abstractSensors/ISensor.h"
#include "../../persistence/EEPROMConfig.h"
#include "../../stateMachine/IState.h"

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

// Forward declaration de estados
class StateIdle;
class StateMonitoring;
class StateIrrigating;
class StateFault;

class DHT11Sketch : public SketchBase {
private:
    IState* currentState;

    ISensor* sensors[MAX_SENSORS];
    uint8_t sensorCount;

    bool _startInAutoMode;

    // Últimas lecturas
    float humiditySoil;
    float humidityAir;
    float temperature;

    // Umbrales y configuración
    float thresholdMin;
    float thresholdMax;
    uint32_t irrigationTimeout;
    ConfigData _config;

    // Seguimiento de fallos por sensor
    uint8_t invalidCounts[MAX_SENSORS];
    bool sensorFaultFlag;

    // Métodos internos
    void setRelay(bool on);
    void checkSensorFault();
    static SensorType sensorTypeFromStr(const char* name);

public:
    DHT11Sketch();
    ~DHT11Sketch();

    // SketchBase interface
    void setup() override;
    void loop() override;

    const char* sketchId() const override { return "dht11"; }
    const char* sketchName() const override { return "12 DHT11"; }
    const char* version() const override { return "1.0"; }

    // Comandos
    void turnRelayOn() override;
    void turnRelayOff() override;
    void setModeAuto() override;
    void setModeManual() override;
    void resetFault() override;
    void setThresholds(float min, float max) override;
    void enableSensor(const char* sensorName) override;
    void disableSensor(const char* sensorName) override;

    // Sensores
    void addSensor(ISensor* sensor);
    void updateSensors();

    // Lecturas
    float getHumidity() const { return humiditySoil; }
    float getHumidityAir() const { return humidityAir; }
    float getTemperature() const { return temperature; }

    // Umbrales
    float getThresholdMin() const { return thresholdMin; }
    float getThresholdMax() const { return thresholdMax; }

    // Sensores enable/disable
    void setSensorEnabled(SensorType type, bool enabled);

    // Estado
    void setState(IState* newState);
    const char* getCurrentStateName() const;

    // Fallo de sensor
    bool hasSensorFault() const { return sensorFaultFlag; }
    void resetSensorFault();

    // Publicación de lecturas
    void publishSensorReadings();

    // Timeout de riego
    uint32_t getIrrigationTimeout() const { return irrigationTimeout; }

    // Modo
    void setStartInAutoMode(bool v);
    bool getStartInAutoMode() const { return _startInAutoMode; }

    uint8_t getSensorCount() const { return sensorCount; }

    // Amistad con estados para que accedan a métodos privados
    friend class StateIdle;
    friend class StateMonitoring;
    friend class StateIrrigating;
    friend class StateFault;
};

#endif