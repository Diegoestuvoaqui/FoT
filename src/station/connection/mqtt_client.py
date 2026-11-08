import json
import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTEventBus:
    """
    Cliente MQTT de la estación con routing por topic pattern.
    Los observers se registran con un filtro de topic (wildcards MQTT).

    paho-mqtt 2.x (CallbackAPIVersion.VERSION2):
    - connect_async + loop_start: reconexión automática con retardo creciente.
    - Los callbacks v2 reciben reason_code / properties adicionales.
    """

    def __init__(self, broker_ip: str, broker_port: int = 1883):
        self._broker_ip = broker_ip
        self._broker_port = broker_port
        self._observers: list[tuple[object, str]] = []  # (observer, topic_filter)
        self._client: mqtt.Client | None = None
        self._credentials: tuple[str, str] | None = None
        self._on_disconnect_cb = None  # callable(reason_code) -> None

    # ------------------------------------------------------------------
    # Registro de observers
    # ------------------------------------------------------------------
    def register(self, observer, topic_filter: str = "#") -> None:
        """
        Wildcards MQTT: + (un nivel), # (múltiples niveles, solo al final).
        Ejemplos:
            "fot/+/sensores"  -> todas las lecturas
            "fot/board-01/#"  -> todo de board-01
        """
        if not hasattr(observer, 'on_event'):
            raise ValueError("Observer debe tener metodo on_event(topic, data)")
        self._observers.append((observer, topic_filter))
        logger.debug("Observer registrado para %s: %s",
                     topic_filter, type(observer).__name__)

    def unregister(self, observer) -> None:
        self._observers = [(o, f) for o, f in self._observers if o is not observer]

    def _notify(self, topic: str, data: dict) -> None:
        for observer, topic_filter in self._observers:
            if self._topic_matches(topic_filter, topic):
                try:
                    observer.on_event(topic, data)
                except Exception as e:
                    logger.error("Error en observer %s: %s",
                                 type(observer).__name__, e)

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """
        Matcher MQTT real (a diferencia de fnmatch, respeta los '/'):
        + coincide con exactamente un nivel; # con cero o más niveles finales.
        """
        if topic.startswith("$") and not pattern.startswith("$"):
            return False  # los topics $SYS no se capturan con wildcards
        p = pattern.split("/")
        t = topic.split("/")
        for i, seg in enumerate(p):
            if seg == "#":
                return i == len(p) - 1  # '#' solo es valido al final
            if i >= len(t):
                return False
            if seg != "+" and seg != t[i]:
                return False
        return len(p) == len(t)

    # ------------------------------------------------------------------
    # Credenciales (se usan en la Fase 7, modo "secure")
    # ------------------------------------------------------------------
    def set_credentials(self, username: str, password: str) -> None:
        self._credentials = (username, password)
        if self._client is not None:
            self._client.username_pw_set(username, password)

    def set_on_disconnect(self, callback) -> None:
        """callback(reason_code: int) -> None, llamado desde el hilo de paho."""
        self._on_disconnect_cb = callback

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected())

    def start(self) -> None:
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self._credentials:
            self._client.username_pw_set(*self._credentials)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        # connect_async (no bloqueante) + loop_start: ante una caida del
        # broker, paho reintenta solo con retardo creciente 1s -> 30s.
        self._client.connect_async(self._broker_ip, self._broker_port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    # ------------------------------------------------------------------
    # Callbacks paho v2
    # ------------------------------------------------------------------
    def _on_connect(self, client: mqtt.Client, _userdata: object,
                    _flags: mqtt.ConnectFlags,
                    reason_code: mqtt.ReasonCode,
                    _properties: object | None = None) -> None:
        if reason_code.is_failure:
            logger.warning("MQTT conexion rechazada: %s", reason_code)
            return
        client.subscribe("fot/+/sensores", qos=1)
        client.subscribe("fot/+/estado", qos=1)
        logger.info("MQTT conectado a %s:%s", self._broker_ip, self._broker_port)

    def _on_disconnect(self, _client: mqtt.Client, _userdata: object,
                       _disconnect_flags: mqtt.DisconnectFlags,
                       reason_code: mqtt.ReasonCode,
                       _properties: object | None = None) -> None:
        logger.warning("MQTT desconectado: %s (reintentando...)", reason_code)
        if self._on_disconnect_cb:
            try:
                self._on_disconnect_cb(reason_code)
            except Exception as e:
                logger.error("Error en callback on_disconnect: %s", e)

    def _on_message(self, _client: mqtt.Client, _userdata: object,
                    message: mqtt.MQTTMessage) -> None:
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Payload no es JSON valido en %s: %s",
                           message.topic, e)
            return
        self._notify(message.topic, data)

    # ------------------------------------------------------------------
    # Publicación
    # ------------------------------------------------------------------
    def publish(self, topic: str, payload: dict,
                qos: int = 1, retain: bool = False) -> None:
        if self._client:
            self._client.publish(topic, json.dumps(payload), qos=qos, retain=retain)
        else:
            logger.warning("publish() sin cliente activo -- topic: %s", topic)
