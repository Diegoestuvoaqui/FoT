#include "StateFault.h"
#include "StateMachine.h"
#include "StateIdle.h"
// reemplazar: para los test
//#include <Arduino.h>
// por:
#ifdef ARDUINO
#include <Arduino.h>
#else
#include "ArduinoMock.h"
#endif

StateFault::StateFault(const char *type)
    : faultType(type)
      , _reported(false) {
}

void StateFault::handle(StateMachine &ctx) {
    // 1. Forzar relay apagado
    ctx.turnRelayOff();

    // 2. Publicar tipo de fallo solo al entrar por primera vez
    if (!_reported) {
        _reported = true;
        Serial.print("FAULT: ");
        Serial.println(faultType);
        // TODO: publicar en MQTT faultType en topic "fot/<parcela>/estado"
    }

    // 3. Solo reset_fault permite salir
    const char *cmd = ctx.getPendingCommand();
    if (cmd && strncmp(cmd, "reset_fault", 11) == 0) {
        ctx.clearPendingCommand();
        ctx.resetSensorFault();
        ctx.setState(new StateIdle());
        return;
    }

    ctx.clearPendingCommand();
}

const char *StateFault::name() const { return "Fault"; }
