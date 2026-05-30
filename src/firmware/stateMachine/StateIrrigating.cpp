#include "StateIrrigating.h"
#include "StateMachine.h"
#include "StateIdle.h"
#include "StateMonitoring.h"
#include "StateFault.h"
#include <Arduino.h>

StateIrrigating::StateIrrigating(bool autoOrigin)
    : cameFromAuto(autoOrigin)
    , startTime(0)
    , firstTick(true)
{}


    

void StateIrrigating::handle(StateMachine& ctx) {
    // 1. Activar relay siempre (ya está encendido desde la transición, redundante pero seguro)
    ctx.turnRelayOn();

    // 2. Registrar tiempo de inicio
    if (firstTick) {
        startTime = millis();
        firstTick = false;
    }

    // 3. Lectura periódica de sensores
    ctx.updateSensors();

    // 4. Condiciones de salida:

    // a) Humedad alcanzó el máximo
    if (ctx.getHumidity() >= ctx.getThresholdMax()) {
        ctx.turnRelayOff();
        if (cameFromAuto) {
            ctx.setState(new StateMonitoring());
        } else {
            ctx.setState(new StateIdle());
        }
        return;
    }

    // b) Timeout de seguridad
    uint32_t elapsed = (millis() - startTime) / 1000UL; // en segundos
    if (elapsed >= ctx.getIrrigationTimeout()) {
        ctx.turnRelayOff();
        ctx.setState(new StateFault("irrigation_timeout"));
        return;
    }

    // c) Comando stop
    const char* cmd = ctx.getPendingCommand();
    if (cmd && strncmp(cmd, "stop", 4) == 0) {
        ctx.turnRelayOff();
        ctx.clearPendingCommand();
        if (cameFromAuto) {
            ctx.setState(new StateMonitoring());
        } else {
            ctx.setState(new StateIdle());
        }
        return;
    }

    // d) Fallo de sensor (3 lecturas inválidas consecutivas en sensor habilitado)
    if (ctx.hasSensorFault()) {
        ctx.turnRelayOff();
        ctx.setState(new StateFault("sensor_invalid"));
        return;
    }


}

// StateIrrigating.cpp TEST
const char* StateIrrigating::name() const { return "Irrigating"; }