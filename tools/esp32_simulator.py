#!/usr/bin/env python3
"""Simula un ESP32 + DHT22 + relé por MQTT.

Uso:
    python3 tools/esp32_simulator.py
    python3 tools/esp32_simulator.py --board-id esp32-002 --interval 3000

Mientras corre, la app ve la placa como si fuera real:
- Publica estado al conectar (con LWT offline).
- Publica lecturas cada --interval ms.
- Responde a read/identify/interval/relay.
- Ackea el relé con {ack, id, state, seq}.
"""
import argparse
import json
import random
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt


class Esp32Simulator:
    def __init__(self, board_id: str, host: str, port: int,
                 interval_ms: int = 5000):
        self.board_id = board_id
        self.host = host
        self.port = port
        self.interval_ms = interval_ms
        self.relay_state = 0
        self._stop = False

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=board_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        will_topic = f"fot/{board_id}/estado"
        will_payload = json.dumps({"status": "offline"})
        self.client.will_set(will_topic, will_payload, qos=1, retain=True)

    def start(self):
        self.client.connect(self.host, self.port)
        self.client.loop_start()
        threading.Thread(target=self._loop_readings, daemon=True).start()

    def stop(self):
        self._stop = True
        self._publish_state("offline")
        time.sleep(0.2)
        self.client.loop_stop()
        self.client.disconnect()

    # --- Callbacks ---
    def _on_connect(self, client, userdata, flags, reason_code, props):
        print(f"[SIM] Conectado al broker ({reason_code})")
        client.subscribe(f"fot/{self.board_id}/control", qos=1)
        self._publish_state("online", boot=True)

    def _on_disconnect(self, client, userdata, flags, reason_code, props):
        if reason_code.is_failure:
            print(f"[SIM] Desconectado: {reason_code}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except Exception:
            return
        cmd = data.get("cmd")
        if cmd == "read":
            self._publish_reading()
        elif cmd == "identify":
            self._publish_state("online")
        elif cmd == "interval":
            self.interval_ms = int(data.get("ms", self.interval_ms))
            print(f"[SIM] Intervalo -> {self.interval_ms} ms")
        elif cmd == "relay":
            state = int(data.get("state", 0))
            seq = int(data.get("seq", 0))
            self.relay_state = state
            print(f"[SIM] Relé -> {'ON' if state else 'OFF'} (seq={seq})")
            self._publish_ack(seq)

    # --- Publicaciones ---
    def _publish_reading(self):
        temp = 24.0 + random.uniform(-2.0, 2.0)
        hum = 60.0 + random.uniform(-8.0, 8.0)
        payload = {
            "data": {
                "temp": {"value": round(temp, 1), "unit": "C"},
                "hum": {"value": round(hum, 1), "unit": "%"},
            },
            "ts": int(time.time() * 1000) & 0xFFFFFFFF,
        }
        self.client.publish(
            f"fot/{self.board_id}/sensores", json.dumps(payload), qos=1)
        print(f"[SIM] Lectura: {temp:.1f}C, {hum:.1f}%")

    def _publish_state(self, status: str, boot: bool = False):
        payload = {
            "sketch": "esp32_wifi_dht22",
            "name": "ESP32 + DHT22",
            "version": "1.0.0",
            "hw": "esp32",
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.1.100",
            "rssi": -60,
            "sensors": 2,
            "actuators": 1,
            "interval_ms": self.interval_ms,
            "power_mode": "normal",
            "relay": self.relay_state,
            "status": status,
        }
        if boot:
            payload["boot"] = True
        self.client.publish(
            f"fot/{self.board_id}/estado", json.dumps(payload), qos=1)

    def _publish_ack(self, seq: int):
        payload = {
            "ack": "relay",
            "id": "relay1",
            "state": self.relay_state,
            "seq": seq,
        }
        self.client.publish(
            f"fot/{self.board_id}/estado", json.dumps(payload), qos=1)

    def _loop_readings(self):
        while not self._stop:
            time.sleep(self.interval_ms / 1000.0)
            if not self._stop:
                self._publish_reading()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board-id", default="esp32-sim-01")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--interval", type=int, default=5000)
    args = ap.parse_args()

    sim = Esp32Simulator(args.board_id, args.host, args.port, args.interval)
    sim.start()

    def _stop(_s, _f):
        sim.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    print(f"[SIM] {args.board_id} simulando en {args.host}:{args.port} "
          f"(intervalo {args.interval}ms)")
    print("[SIM] Ctrl+C para detener")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()