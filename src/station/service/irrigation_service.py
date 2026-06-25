# service/irrigation_service.py
import logging

logger = logging.getLogger(__name__)


class IrrigationService:
    """
    Orquesta el envío de comandos de riego a las parcelas.
    Decide el canal: SerialBridge (USB directo) o MQTT (fallback WiFi).
    """

    def __init__(self, board_service, mqtt_bus, event_service):
        self._board_service = board_service
        self._mqtt_bus = mqtt_bus
        self._event_service = event_service

    # ------------------------------------------------------------------
    # Comandos públicos
    # ------------------------------------------------------------------
    def irrigate(self, parcela_id: str) -> None:
        """Activa el riego en una parcela."""
        self._send_command(parcela_id, {"cmd": "irrigate"})
        self._event_service.log(
            parcela_id=parcela_id,
            descripcion=f"Riego activado en {parcela_id}",
            tipo="riego"
        )

    def stop(self, parcela_id: str) -> None:
        """Detiene el riego en una parcela."""
        self._send_command(parcela_id, {"cmd": "stop"})
        self._event_service.log(
            parcela_id=parcela_id,
            descripcion=f"Riego detenido en {parcela_id}",
            tipo="riego"
        )

    def set_mode(self, parcela_id: str, mode: str) -> None:
        """
        Cambia el modo de una parcela.
        mode: 'auto' o 'manual'
        """
        if mode not in ("auto", "manual"):
            raise ValueError(f"Modo inválido: {mode}")

        cmd = "set_mode_auto" if mode == "auto" else "set_mode_manual"
        self._send_command(parcela_id, {"cmd": cmd})
        self._event_service.log(
            parcela_id=parcela_id,
            descripcion=f"Modo cambiado a '{mode}' en {parcela_id}",
            tipo="modo"
        )

    def set_thresholds(self, parcela_id: str, min_val: float, max_val: float) -> None:
        """
        Establece los umbrales de humedad de una parcela.
        """
        self._send_command(parcela_id, {
            "cmd": "set_thresholds",
            "min": min_val,
            "max": max_val
        })

    # ------------------------------------------------------------------
    # Enrutamiento interno
    # ------------------------------------------------------------------
    def _send_command(self, parcela_id: str, payload: dict) -> None:
        """
        Intenta enviar por SerialBridge; si no hay, fallback a MQTT.
        """
        bridge = self._board_service.get_bridge_for_parcela(parcela_id)
        if bridge:
            bridge.send_command(payload)
            logger.debug("Comando enviado por SerialBridge a %s", parcela_id)
        else:
            topic = f"fot/{parcela_id}/control"
            self._mqtt_bus.publish(topic, payload)
            logger.debug("Comando enviado por MQTT a %s", parcela_id)
