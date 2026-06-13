#include "StateIrrigating.h"
#include "StateMachine.h"
#include "StateIdle.h"
#include "StateMonitoring.h"
#include "StateFault.h"
// reemplazar: para los test
//#include <Arduino.h>
// por:
#ifdef ARDUINO
#include <Arduino.h>
#else
#include "ArduinoMock.h"
#endif

StateIrrigating::StateIrrigating(bool autoOrigin)
    : cameFromAuto(autoOrigin)
      , startTime(0)
      , firstTick(true)
      , lastSensorUpdate(0) {
}


void StateIrrigating::handle(StateMachine &ctx) {
    // 1. Relay siempre encendido
    ctx.turnRelayOn();

    // 2. Registrar tiempo de inicio
    if (firstTick) {
        startTime = millis();
        firstTick = false;
    }

    // 3. Lectura periódica — igual que StateIdle y StateMonitoring
    if (millis() - lastSensorUpdate >= SENSOR_READ_INTERVAL) {
        lastSensorUpdate = millis();
        ctx.updateSensors();

        // a) Humedad alcanzó el máximo
        if (ctx.getHumidity() >= ctx.getThresholdMax()) {
            ctx.turnRelayOff();
            if (cameFromAuto) ctx.setState(new StateMonitoring());
            else ctx.setState(new StateIdle());
            return;
        }

        // b) Fallo de sensor
        if (ctx.hasSensorFault()) {
            ctx.turnRelayOff();
            ctx.setState(new StateFault("sensor_invalid"));
            return;
        }
    }

    // 4. Timeout — se evalúa cada tick para ser responsivo
    uint32_t elapsed = (millis() - startTime) / 1000UL;
    if (elapsed >= ctx.getIrrigationTimeout()) {
        ctx.turnRelayOff();
        ctx.setState(new StateFault("irrigation_timeout"));
        return;
    }

    // 5. Comando stop — también cada tick
    const char *cmd = ctx.getPendingCommand();
    if (cmd && strncmp(cmd, "stop", 4) == 0) {
        ctx.turnRelayOff();
        ctx.clearPendingCommand();
        if (cameFromAuto) ctx.setState(new StateMonitoring());
        else ctx.setState(new StateIdle());
        return;
    }
}

// StateIrrigating.cpp TEST
const char *StateIrrigating::name() const { return "Irrigating"; }
