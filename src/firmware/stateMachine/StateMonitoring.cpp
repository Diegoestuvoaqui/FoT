#include "StateMonitoring.h"
#include "StateMachine.h"
#include "StateIdle.h"
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

StateMonitoring::StateMonitoring()
    : lastSensorUpdate(0) {
}

void StateMonitoring::handle(StateMachine &ctx) {
    // 1. Asegurar relay apagado mientras evalúa
    ctx.turnRelayOff();

    // 2. Lectura periódica
    if (millis() - lastSensorUpdate >= SENSOR_READ_INTERVAL) {
        lastSensorUpdate = millis();
        ctx.updateSensors();
        ctx.publishSensorReadings();

        // Fallo de sensor
        if (ctx.hasSensorFault()) {
            ctx.setState(new StateFault("sensor_invalid"));
            return;
        }

        // Evaluar umbral: si humedad < mínimo -> regar automáticamente
        if (ctx.getHumidity() < ctx.getThresholdMin()) {
            ctx.setState(new StateIrrigating(true)); // _cameFromAuto = true
            return;
        }
    }

    // 3. Procesar comandos
    const char *cmd = ctx.getPendingCommand();
    if (cmd) {
        if (strncmp(cmd, "set_mode_manual", 15) == 0) {
            ctx.setStartInAutoMode(false);
            ctx.setState(new StateIdle());
        }
        // irrigate y stop son ignorados en modo automático
        // enable/disable/thresholds ya fueron manejados por dispatch
        ctx.clearPendingCommand();
    }
}

const char *StateMonitoring::name() const { return "Monitoring"; }

