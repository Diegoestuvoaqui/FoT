"""Broker MQTT embebido (amqtt) en un hilo daemon con su propio event loop.

La estación es su propio broker: arranca y se detiene con la app, sin
Mosquitto ni ningún servicio externo.

- asyncio queda aislado DENTRO de este hilo; el resto de la app (paho,
  Tkinter) sigue en su mundo de hilos.
- En modo "open" (desarrollo) acepta conexiones anónimas.
- En modo "secure" (Fase 7) se carga connection.broker_security.FotAccessPlugin.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from amqtt.broker import Broker

logger = logging.getLogger(__name__)


class EmbeddedBroker:
    """Envoltura síncrona (hilos) alrededor del broker asyncio de amqtt."""

    def __init__(self, host: str = "0.0.0.0", port: int = 1883,
                 auth_mode: str = "open", auth_config: dict | None = None):
        if auth_mode not in ("open", "secure"):
            raise ValueError("auth_mode debe ser 'open' o 'secure'")
        self._host = host
        self._port = port
        self._auth_mode = auth_mode
        self._auth_config = auth_config or {}

        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._broker: Broker | None = None
        self._ready = threading.Event()
        self._stop_requested = threading.Event()
        self._start_error: BaseException | None = None

    # ------------------------------------------------------------------
    @property
    def _config(self) -> dict:
        listeners = {
            "default": {
                "type": "tcp",
                "bind": f"{self._host}:{self._port}",
            }
        }
        if self._auth_mode == "open":
            plugins = {
                "amqtt.plugins.logging_amqtt.EventLoggerPlugin": {},
                "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                    "allow_anonymous": True,
                },
            }
        else:
            # Fase 7 — autenticación y ACL por dispositivo contra la BD.
            plugins = {
                "amqtt.plugins.logging_amqtt.EventLoggerPlugin": {},
                "connection.broker_security.FotAccessPlugin": self._auth_config,
            }
        return {"listeners": listeners, "plugins": plugins}

    # ------------------------------------------------------------------
    def start(self, timeout: float = 10.0) -> None:
        """Arranca el broker y espera a que esté listo. Lanza RuntimeError si falla."""
        if self.is_running():
            return
        self._stop_requested.clear()
        self._ready.clear()
        self._start_error = None
        self._thread = threading.Thread(
            target=self._run, name="amqtt-broker", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError(
                f"El broker no arranco en {timeout:.0f}s "
                f"(puerto {self._port} ocupado o error de red)")
        if self._start_error is not None:
            raise RuntimeError(
                f"Fallo al iniciar el broker: {self._start_error}")

    def stop(self) -> None:
        """Pide el cierre del broker y espera a que el hilo termine."""
        if not self._thread:
            return
        self._stop_requested.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._wake_serve)
        self._thread.join(timeout=5)
        self._thread = None
        self._broker = None
        logger.info("Broker embebido detenido")

    def is_running(self) -> bool:
        return (self._thread is not None and self._thread.is_alive()
                and self._ready.is_set() and self._broker is not None)

    # ------------------------------------------------------------------
    # Internos — todo lo asyncio ocurre dentro del hilo del broker
    # ------------------------------------------------------------------
    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:  # noqa: BLE001 — se re-lanza en start()
            self._start_error = e
            logger.exception("Error en el hilo del broker")
        finally:
            self._loop.close()
            self._loop = None

    async def _serve(self) -> None:
        self._wake = asyncio.Event()  # creado DENTRO del loop correcto
        self._broker = Broker(self._config)
        try:
            await self._broker.start()
        except Exception as e:  # noqa: BLE001
            self._start_error = e
            self._ready.set()  # desbloquea start() para que lance el error
            return
        self._ready.set()
        logger.info("Broker amqtt escuchando en %s:%s (modo %s)",
                    self._host, self._port, self._auth_mode)
        await self._wake.wait()  # duerme hasta que stop() lo despierte
        try:
            await self._broker.shutdown()
        except Exception as e:  # noqa: BLE001
            logger.error("Error al apagar el broker: %s", e)

    def _wake_serve(self) -> None:
        """Se ejecuta dentro del loop del broker vía call_soon_threadsafe."""
        self._wake.set()
