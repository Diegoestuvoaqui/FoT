import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTEventBus:

    def __init__(self, broker_ip: str, broker_port: int = 1883):
        self._broker_ip = broker_ip
        self._broker_port = broker_port
        self._observers: list = []
        self._client: mqtt.Client | None = None

    # --------------------------------------------------------------------------
    # Gestión de observers
    # --------------------------------------------------------------------------
    def register(self, observer) -> None:
        """Registra un observer. Debe implementar on_event(topic, data)."""
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister(self, observer) -> None:
        self._observers = [o for o in self._observers if o is not observer]

    def _notify(self, topic: str, data: dict) -> None:
        """Notifica a todos los observers. Una excepción individual no detiene la cadena."""
        for observer in self._observers:
            try:
                observer.on_event(topic, data)
            except Exception as e:
                logger.error("Error en observer %s: %s", type(observer).__name__, e)

    # --------------------------------------------------------------------------
    # Ciclo de vida
    # --------------------------------------------------------------------------
    def start(self) -> None:
        """Crea el cliente, registra callbacks y arranca el hilo de red."""
        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(self._broker_ip, self._broker_port, keepalive=60)
        self._client.loop_start()  # hilo de red en segundo plano

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    # --------------------------------------------------------------------------
    # Callbacks internos de paho
    # --------------------------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            client.subscribe("fot/+/sensores", qos=1)
            client.subscribe("fot/+/estado", qos=1)
            logger.info("MQTT conectado a %s:%s", self._broker_ip, self._broker_port)
        else:
            logger.warning("MQTT conexión rechazada, rc=%s", rc)

    def _on_message(self, client, userdata, message) -> None:
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.warning("Payload no es JSON válido en %s: %s", message.topic, e)
            return
        self._notify(message.topic, data)

    # --------------------------------------------------------------------------
    # Publicación
    # --------------------------------------------------------------------------
    def publish(self, topic: str, payload: dict) -> None:
        if self._client:
            self._client.publish(topic, json.dumps(payload), qos=1)
        else:
            logger.warning("publish() llamado sin cliente activo — topic: %s", topic)
