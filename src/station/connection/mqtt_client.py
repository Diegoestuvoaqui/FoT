import json
import fnmatch
import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTEventBus:
    """
    Broker MQTT con routing por topic pattern.
    Los observers se registran con un filtro de topic (wildcard soportado).
    """

    def __init__(self, broker_ip: str, broker_port: int = 1883):
        self._broker_ip = broker_ip
        self._broker_port = broker_port
        self._observers: list[tuple[object, str]] = []  # (observer, topic_filter)
        self._client: mqtt.Client | None = None

    def register(self, observer, topic_filter: str = "#") -> None:
        """
        Registra un observer para un pattern de topic.
        Wildcards MQTT: + (un nivel), # (múltiples niveles)
        Ejemplos:
            "fot/+/sensores"     → todas las lecturas
            "fot/board-01/#"     → todo de board-01
            "#"                   → todo (default)
        """
        if not hasattr(observer, 'on_event'):
            raise ValueError("Observer debe tener método on_event(topic, data)")
        self._observers.append((observer, topic_filter))
        logger.debug("Observer registrado para %s: %s", topic_filter, type(observer).__name__)

    def unregister(self, observer) -> None:
        self._observers = [(o, f) for o, f in self._observers if o is not observer]

    def _notify(self, topic: str, data: dict) -> None:
        for observer, topic_filter in self._observers:
            if self._topic_matches(topic_filter, topic):
                try:
                    observer.on_event(topic, data)
                except Exception as e:
                    logger.error("Error en observer %s: %s", type(observer).__name__, e)

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """
        Convierte pattern MQTT a regex de fnmatch.
        + → un solo nivel cualquiera
        # → múltiples niveles (solo al final)
        """
        pattern_glob = pattern.replace("+", "*").replace("#", "*")
        return fnmatch.fnmatch(topic, pattern_glob)

    def start(self) -> None:
        self._client = mqtt.Client()
        assert self._client is not None
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(self._broker_ip, self._broker_port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def _on_connect(self, client: mqtt.Client, _userdata: object,
                    _flags: dict, rc: int) -> None:
        if rc == 0:
            client.subscribe("fot/+/sensores", qos=1)
            client.subscribe("fot/+/estado", qos=1)
            logger.info("MQTT conectado a %s:%s", self._broker_ip, self._broker_port)
        else:
            logger.warning("MQTT conexión rechazada, rc=%s", rc)

    def _on_message(self, _client: mqtt.Client, _userdata: object,
                    message: mqtt.MQTTMessage) -> None:
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.warning("Payload no es JSON válido en %s: %s", message.topic, e)
            return
        self._notify(message.topic, data)

    def publish(self, topic: str, payload: dict) -> None:
        if self._client:
            self._client.publish(topic, json.dumps(payload), qos=1)
        else:
            logger.warning("publish() llamado sin cliente activo — topic: %s", topic)
