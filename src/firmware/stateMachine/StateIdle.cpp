#include "StateIdle.h"
#include "StateMachine.h"
#include "StateMonitoring.h"
#include "StateIrrigating.h"
#include "StateFault.h"
// reemplazar: para los test
//#include <Arduino.h>
// por:
#ifdef ARDUINO
  #include <Arduino.h>
#else
  #include "ArduinoMock.h"
#endif

StateIdle::StateIdle()
    : lastSensorUpdate(0)
{}

void StateIdle::handle(StateMachine& ctx) {
    // 1. Leer sensores periódicamente
    if (millis() - lastSensorUpdate >= SENSOR_READ_INTERVAL) {
        lastSensorUpdate = millis();
        ctx.updateSensors();

        // Publicar lecturas
        ctx.publishSensorReadings();

        // Verificar fallo de sensor
        if (ctx.hasSensorFault()) {
            ctx.setState(new StateFault("sensor_invalid"));
            return;
        }
    }

    // 2. Procesar comando pendiente
    const char* cmd = ctx.getPendingCommand();
    if (cmd) {
        if (strncmp(cmd, "irrigate", 8) == 0) {
            ctx.turnRelayOn();
            ctx.setState(new StateIrrigating(false));
        }
        else if (strncmp(cmd, "stop", 4) == 0) {
            ctx.turnRelayOff();
            // permanece en Idle
        }
        else if (strncmp(cmd, "set_mode_auto", 13) == 0) {
            ctx.setStartInAutoMode(true);
            ctx.setState(new StateMonitoring());
        }
        // reset_fault no aplica en Idle, ignorar
        // enable_sensor/disable_sensor/set_thresholds gestionados por dispatchCommand
        ctx.clearPendingCommand();
    }

}


    // StateIdle.cpp TEST
    const char* StateIdle::name() const { return "Idle"; }