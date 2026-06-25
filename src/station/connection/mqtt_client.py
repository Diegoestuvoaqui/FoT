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

    def register(self, observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister(self, observer) -> None:
        self._observers = [o for o in self._observers if o is not observer]

    def _notify(self, topic: str, data: dict) -> None:
        for observer in self._observers:
            try:
                observer.on_event(topic, data)
            except Exception as e:
                logger.error("Error en observer %s: %s", type(observer).__name__, e)

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

    # Firma exacta que espera paho — prefijo _ en los no usados
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
