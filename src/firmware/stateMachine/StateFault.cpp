#include "StateFault.h"
#include "StateMachine.h"
#include "StateIdle.h"
#include <Arduino.h>

StateFault::StateFault(const char* type)
    : faultType(type)
{}

void StateFault::handle(StateMachine& ctx) {
    // 1. Forzar relay apagado
    ctx.turnRelayOff();

    // 2. Publicar tipo de fallo (una sola vez, por ejemplo al entrar,
    //    pero aquí lo hacemos cada tick; en producción podrías usar una bandera)
    // TODO: publicar en MQTT el faultType en topic "fot/<parcela>/estado"
    Serial.print("FAULT: ");
    Serial.println(faultType);

    // 3. Solo se permite reset_fault para salir
    const char* cmd = ctx.getPendingCommand();
    if (cmd && strncmp(cmd, "reset_fault", 11) == 0) {
        ctx.clearPendingCommand();
        ctx.resetSensorFault(); // limpiar contadores de fallo
        ctx.setState(new StateIdle());
        return;
    }

    // Ignorar cualquier otro comando
    ctx.clearPendingCommand();
}