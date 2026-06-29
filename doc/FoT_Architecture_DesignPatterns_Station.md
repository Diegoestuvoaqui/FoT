
# Farm of Things (FoT) — Documentación Técnica

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Requisitos Funcionales](#requisitos-funcionales)
4. [Requisitos No Funcionales](#requisitos-no-funcionales)
5. [Patrones de Diseño GoF](#patrones-de-diseño-gof)
6. [Patrones de Diseño Arquitectónicos](#patrones-de-diseño-arquitectónicos)
7. [Estructura de Carpetas](#estructura-de-carpetas)
8. [Diagrama de Capas](#diagrama-de-capas)
9. [Flujo de Datos](#flujo-de-datos)
10. [Tecnologías y Dependencias](#tecnologías-y-dependencias)

---

## Visión General

**Farm of Things (FoT)** es una aplicación de escritorio para monitoreo de sensores IoT (Internet of Things) diseñada para comunicarse con placas Arduino. La estación base actúa como hub central que recopila datos de sensores (temperatura, humedad, etc.) a través de múltiples protocolos de comunicación (USB serial, Bluetooth, WiFi/MQTT) y los presenta en una interfaz gráfica moderna.

### Características Principales
- **Multi-conexión**: Soporta USB, Bluetooth (HC-05/06) y WiFi (Arduino UNO R4)
- **Monitoreo en tiempo real**: Visualización de lecturas de sensores con historial
- **Gestión de usuarios**: Sistema de autenticación con roles (admin/user)
- **Exportación de datos**: CSV y JSON con filtros por fecha y tipo de sensor
- **Firmware remoto**: Carga de firmware `.hex` mediante `avrdude`
- **Notificaciones**: Sistema de toast notifications con sonido y historial
- **Snapshots**: Copias de seguridad de configuración
- **Auto-detección**: Escaneo automático de puertos USB

---

## Arquitectura del Sistema

La aplicación sigue una **Arquitectura en Capas (Layered Architecture)** con separación clara de responsabilidades, complementada con patrones de **Observer** y **MVC (Model-View-Controller)** adaptado.

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTACIÓN (UI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Panels  │ │ Dialogs  │ │ Widgets  │ │  Theme   │      │
│  │ DHT11    │ │ Login    │ │ SideBar  │ │          │      │
│  │ Arduino  │ │ Export   │ │ TopBar   │ │          │      │
│  │ Admin    │ │ Firmware │ │ StatusBar│ │          │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────┤
│                   CONTROLADORES (Controller)               │
│  AuthCtrl │ BoardCtrl │ EventCtrl │ ExportCtrl │ SnapCtrl  │
├─────────────────────────────────────────────────────────────┤
│                    SERVICIOS (Service)                     │
│  AuthSvc │ BoardSvc │ EventSvc │ ExportSvc │ SnapshotSvc  │
├─────────────────────────────────────────────────────────────┤
│                     LÓGICA DE NEGOCIO (Logic)              │
│  SerialBridge │ BluetoothBridge │ WiFiBridge │ SensorMgr   │
│  DataReceiver │ Exporter │ FirmwareUploader │ USBScanner  │
├─────────────────────────────────────────────────────────────┤
│                      DOMINIO (Domain)                      │
│  Board │ User │ ConfigSnapshot │ ConfigManager             │
├─────────────────────────────────────────────────────────────┤
│                     INFRAESTRUCTURA (Data)                 │
│  Database (SQLite) │ MQTTEventBus │ Bootstrap                │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Comunicación

```
UI → Controller → Service → Logic → Domain → Data
  ↑______________________________________________|
           (Observer pattern para notificaciones)
```

---

## Requisitos Funcionales

### RF-01: Autenticación y Autorización
- **RF-01.1**: El sistema debe permitir el inicio de sesión con usuario y contraseña.
- **RF-01.2**: El sistema debe permitir el registro de nuevos usuarios (primer usuario como admin).
- **RF-01.3**: Los administradores pueden gestionar usuarios (listar, eliminar, activar/desactivar, resetear contraseña).
- **RF-01.4**: Los usuarios deben poder cambiar su propia contraseña.
- **RF-01.5**: Contraseñas temporales generadas por admin deben forzar cambio al primer login.

### RF-02: Gestión de Placas (Boards)
- **RF-02.1**: Registrar placas Arduino por USB, Bluetooth o WiFi.
- **RF-02.2**: Auto-detectar placas USB conectadas mediante escaneo de puertos seriales.
- **RF-02.3**: Escanear y registrar dispositivos Bluetooth (HC-05/06) emparejados.
- **RF-02.4**: Escanear y registrar dispositivos WiFi (Arduino UNO R4) en la red local.
- **RF-02.5**: Conectar/desconectar placas individualmente.
- **RF-02.6**: Eliminar placas del sistema.
- **RF-02.7**: Mostrar datos de fábrica del chip (VID, PID, serial number, fabricante).
- **RF-02.8**: Identificar automáticamente el sketch cargado en la placa.

### RF-03: Monitoreo de Sensores
- **RF-03.1**: Visualizar lecturas en tiempo real de sensores DHT11 (temperatura y humedad).
- **RF-03.2**: Mostrar historial de lecturas con timestamps.
- **RF-03.3**: Solicitar lectura manual (comando `read`).
- **RF-03.4**: Configurar intervalo de lectura automática (comando `interval`).
- **RF-03.5**: Almacenar lecturas en base de datos SQLite con timestamp de Arduino y de la estación base.

### RF-04: Comunicación
- **RF-04.1**: Comunicación serial USB con protocolo JSON.
- **RF-04.2**: Comunicación Bluetooth serial (RFCOMM).
- **RF-04.3**: Comunicación WiFi mediante MQTT (broker Mosquitto local).
- **RF-04.4**: Publicación de comandos MQTT hacia placas WiFi.
- **RF-04.5**: Suscripción a topics MQTT para recepción de datos.

### RF-05: Exportación de Datos
- **RF-05.1**: Exportar lecturas de sensores a CSV o JSON.
- **RF-05.2**: Exportar historial de eventos a CSV o JSON.
- **RF-05.3**: Filtrar exportación por rango de fechas.
- **RF-05.4**: Filtrar exportación por tipo de sensor.

### RF-06: Firmware
- **RF-06.1**: Cargar firmware `.hex` a placas Arduino mediante `avrdude`.
- **RF-06.2**: Mostrar progreso de carga en tiempo real.
- **RF-06.3**: Soportar diferentes MCUs (atmega328p por defecto) y programadores.

### RF-07: Notificaciones
- **RF-07.1**: Mostrar notificaciones toast emergentes.
- **RF-07.2**: Reproducir sonidos según tipo de notificación (info, éxito, advertencia, error).
- **RF-07.3**: Mantener historial de notificaciones con estado leído/no leído.
- **RF-07.4**: Badge de notificaciones no leídas en la barra superior.

### RF-08: Configuración y Snapshots
- **RF-08.1**: Crear snapshots manuales de la configuración actual.
- **RF-08.2**: Listar snapshots disponibles.
- **RF-08.3**: Restaurar configuración desde snapshot.
- **RF-08.4**: Cambiar tema de la interfaz (claro/oscuro/sistema).
- **RF-08.5**: Configurar pantalla completa.
- **RF-08.6**: Ajustar volumen y habilitar/deshabilitar sonido de notificaciones.

### RF-09: Eventos y Logging
- **RF-09.1**: Registrar eventos del sistema (conexiones, desconexiones, errores, registros).
- **RF-09.2**: Mostrar log de eventos con filtros (todos, errores, registros).
- **RF-09.3**: Almacenar eventos en base de datos.
- **RF-09.4**: Log de aplicación en archivo (`iot.log`).

### RF-10: Bootstrap y Despliegue
- **RF-10.1**: Verificar dependencias del sistema (Mosquitto, avrdude).
- **RF-10.2**: Configurar Mosquitto automáticamente en primera ejecución.
- **RF-10.3**: Crear servicio systemd de usuario para auto-inicio.
- **RF-10.4**: Asegurar que Mosquitto esté corriendo en cada arranque.

---

## Requisitos No Funcionales

### RNF-01: Rendimiento
- **RNF-01.1**: La interfaz debe responder en menos de 100ms a interacciones del usuario.
- **RNF-01.2**: El escaneo USB no debe bloquear la interfaz (hilo daemon).
- **RNF-01.3**: Las lecturas de sensores deben procesarse y almacenarse en menos de 50ms.
- **RNF-01.4**: El sistema debe soportar al menos 10 placas conectadas simultáneamente.

### RNF-02: Seguridad
- **RNF-02.1**: Las contraseñas deben almacenarse hasheadas (bcrypt preferido, SHA-256 fallback).
- **RNF-02.2**: Validación de roles para operaciones administrativas.
- **RNF-02.3**: No exponer hashes de contraseña en respuestas de API interna.
- **RNF-02.4**: Permitir desactivación de cuentas de usuario.
- **RNF-02.5**: Forzar cambio de contraseña temporal.

### RNF-03: Disponibilidad y Confiabilidad
- **RNF-03.1**: Reconexión automática del broker MQTT tras caída.
- **RNF-03.2**: Timeout de 30 segundos para conexiones WiFi inactivas.
- **RNF-03.3**: Servicio systemd para auto-inicio sin sesión de usuario.
- **RNF-03.4**: Limpieza automática de lecturas antiguas (>30 días).

### RNF-04: Usabilidad
- **RNF-04.1**: Interfaz gráfica moderna con tema oscuro por defecto.
- **RNF-04.2**: Tooltips en elementos de navegación.
- **RNF-04.3**: Notificaciones visuales y sonoras para eventos importantes.
- **RNF-04.4**: Mensajes de error claros en español.
- **RNF-04.5**: Panel de ayuda integrado.

### RNF-05: Escalabilidad
- **RNF-05.1**: Arquitectura modular que permite agregar nuevos tipos de sensores.
- **RNF-05.2**: Patrón Bridge para soportar nuevos protocolos de comunicación.
- **RNF-05.3**: Sistema de plugins implícito mediante sketch identification.

### RNF-06: Mantenibilidad
- **RNF-06.1**: Código organizado en capas con responsabilidad única.
- **RNF-06.2**: Uso de tipado estático (Python type hints).
- **RNF-06.3**: Logging centralizado en todos los módulos.
- **RNF-06.4**: Separación de concerns: UI, lógica, datos.

### RNF-07: Compatibilidad
- **RNF-07.1**: Soportar Linux (Arch/Debian/Ubuntu) como sistema operativo principal.
- **RNF-07.2**: Dependencias declaradas: `mosquitto`, `avrdude`, `python3`.
- **RNF-07.3**: Uso de librerías cross-platform donde sea posible (pyserial, paho-mqtt, customtkinter).

### RNF-08: Persistencia
- **RNF-08.1**: Base de datos SQLite embebida (sin servidor externo).
- **RNF-08.2**: Índices en tablas de lecturas y eventos para consultas rápidas.
- **RNF-08.3**: Configuración de usuario en `~/.config/fot/`.
- **RNF-08.4**: Backup de configuración mediante snapshots.

---

## Patrones de Diseño GoF

### 1. Observer (Observador) — Comportamiento

**Ubicación**: `connection/mqtt_client.py`, `service/event_service.py`, `service/board_service.py`

**Propósito**: Notificar a múltiples componentes cuando ocurre un evento sin acoplar el emisor de los receptores.

**Implementación**:
```python
# MQTTEventBus — Sujeto Observable
class MQTTEventBus:
    def __init__(self, broker_ip, broker_port=1883):
        self._observers = []

    def register(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister(self, observer):
        self._observers = [o for o in self._observers if o is not observer]

    def _notify(self, topic, data):
        for observer in self._observers:
            observer.on_event(topic, data)
```

**Usos**:
- Notificación de lecturas de sensores a múltiples paneles UI
- Eventos del sistema (conexiones, errores)
- Actualización de badges de notificaciones
- Patrón pub/sub interno para desacoplar capas

---

### 2. Singleton (Único) — Creación

**Ubicación**: `ui/widgets/notification_manager.py`

**Propósito**: Garantizar una única instancia del gestor de notificaciones en toda la aplicación.

**Implementación**:
```python
class NotificationManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**Usos**:
- Gestor centralizado de notificaciones
- Historial único de notificaciones
- Configuración de sonido/toast compartida

---

### 3. Strategy (Estrategia) — Comportamiento

**Ubicación**: `logic/exporter.py`

**Propósito**: Permitir diferentes algoritmos de exportación (CSV vs JSON) intercambiables en tiempo de ejecución.

**Implementación**:
```python
class DataExporter:
    def export_readings(self, board_id, ..., fmt="csv", filepath="lecturas.csv"):
        rows = self._db.get_readings(...)
        if fmt == "json":
            return self._write_json(filepath, rows)
        else:
            return self._write_csv(filepath, rows, fieldnames=[...])
```

**Usos**:
- Exportación de datos en múltiples formatos
- Posible extensión a XML, Excel, etc.

---

### 4. Bridge (Puente) — Estructural

**Ubicación**: `logic/serial_bridge.py`, `logic/bluetooth_bridge.py`, `logic/wifi_bridge.py`

**Propósito**: Separar la abstracción de comunicación de su implementación, permitiendo que ambas evolucionen independientemente.

**Implementación**:
```python
# Abstracción
class SerialBridge:
    def __init__(self, port, baud=115200, on_reading=None, on_command_response=None):
        self.port = port
        self.baud = baud
        self._on_reading = on_reading

    def connect(self):
        self._serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
        # ...

    def send_command(self, cmd_dict):
        line = json.dumps(cmd_dict) + "\n"
        self._serial.write(line.encode("utf-8"))

# Refinamiento de abstracción
class BluetoothBridge(SerialBridge):
    def __init__(self, port="/dev/rfcomm0", baud=9600, **kwargs):
        super().__init__(port=port, baud=baud, **kwargs)
```

**Usos**:
- Unificar interfaz de comunicación USB, Bluetooth y WiFi
- SensorManager opera con cualquier Bridge sin conocer su implementación
- Facilita agregar nuevos protocolos (LoRa, Zigbee, etc.)

---

### 5. Adapter (Adaptador) — Estructural

**Ubicación**: `controller/*_controller.py`, `logic/wifi_bridge.py`

**Propósito**: Convertir la interfaz de una clase en otra interfaz que el cliente espera.

**Implementación**:
```python
# WiFiBridge adapta MQTTEventBus a la interfaz de SerialBridge
class WiFiBridge:
    def __init__(self, board_id, mqtt_bus, on_reading=None, on_command_response=None):
        self._mqtt_bus = mqtt_bus
        self._on_reading = on_reading

    def connect(self):
        self._mqtt_bus.register(self)  # Se registra como observer
        return True

    def send_command(self, cmd_dict):
        topic = f"fot/{self.board_id}/comandos"
        self._mqtt_bus.publish(topic, cmd_dict)

    def on_event(self, topic, data):  # Interfaz esperada por MQTTEventBus
        # Adapta a callback on_reading de SerialBridge
        if self._on_reading:
            self._on_reading(data)
```

**Usos**:
- WiFiBridge adapta MQTT a la interfaz serial
- Controllers adaptan Services a la UI
- Permite que SensorManager trate WiFi igual que USB/Bluetooth

---

### 6. Facade (Fachada) — Estructural

**Ubicación**: `logic/sensor_manager.py`

**Propósito**: Proporcionar una interfaz unificada simplificada a un subsistema complejo.

**Implementación**:
```python
class SensorManager:
    def __init__(self, on_reading=None, on_identify=None, mqtt_bus=None):
        self._bridges = {}
        self._on_reading = on_reading
        self._mqtt_bus = mqtt_bus

    def connect_usb(self, port, parcela_id):
        bridge = SerialBridge(port=port, on_reading=...)
        if bridge.connect():
            self._bridges[parcela_id] = bridge
            return True
        return False

    def connect_wifi(self, parcela_id, broker_ip="localhost"):
        bridge = WiFiBridge(board_id=parcela_id, mqtt_bus=self._mqtt_bus, ...)
        if bridge.connect():
            self._bridges[parcela_id] = bridge
            return True
        return False

    def send_command(self, parcela_id, cmd):
        bridge = self._bridges.get(parcela_id)
        if bridge:
            bridge.send_command(cmd)
            return True
        return False
```

**Usos**:
- Oculta complejidad de múltiples protocolos de comunicación
- MainWindow interactúa con un solo SensorManager
- Gestión centralizada de conexiones

---

### 7. Factory Method (Método de Fábrica) — Creación

**Ubicación**: `service/board_service.py`

**Propósito**: Delegar la creación de objetos a subclases o métodos especializados.

**Implementación**:
```python
class BoardService:
    def register_board(self, board_id, port, conn_type="usb", ...):
        board = Board(board_id=board_id, conn=conn_type, port=port, ...)
        self._boards[board_id] = board
        self._persist_board(board)
        return board

    def register_bluetooth_board(self, board_id, port, usuario_id=None):
        return self.register_board(board_id, port, "bluetooth", usuario_id)

    def register_wifi_board(self, board_id, ip, usuario_id=None):
        return self.register_board(board_id, ip, "wifi", usuario_id)
```

**Usos**:
- Creación de boards con diferentes tipos de conexión
- Extensible para nuevos tipos de conexión

---

### 8. Memento (Recuerdo) — Comportamiento

**Ubicación**: `domain/memento.py`

**Propósito**: Capturar y externalizar el estado interno de un objeto para poder restaurarlo posteriormente.

**Implementación**:
```python
class ConfigSnapshot:
    def __init__(self, state, timestamp=""):
        self._state = state
        self._timestamp = timestamp or datetime.now().isoformat()

    def get_state(self):
        return self._state

class ConfigManager:
    def save_snapshot(self, boards, descripcion, db, usuario_id=None):
        state_dict = {"boards": [self._serialize_board(b) for b in boards]}
        state_json = json.dumps(state_dict)
        db.save_snapshot(usuario_id, descripcion, state_json)
        return ConfigSnapshot(state=state_json)

    def restore_snapshot(self, snapshot_id, db):
        row = db.get_snapshot(snapshot_id)
        return json.loads(row["datos_json"])
```

**Usos**:
- Backup de configuración de placas
- Restauración de estado previo
- Historial de configuraciones

---

### 9. Command (Comando) — Comportamiento

**Ubicación**: `logic/serial_bridge.py`

**Propósito**: Encapsular una solicitud como un objeto, permitiendo parametrizar clientes con diferentes solicitudes.

**Implementación**:
```python
class SerialBridge:
    def send_command(self, cmd_dict):
        line = json.dumps(cmd_dict) + "\n"
        self._serial.write(line.encode("utf-8"))

    def request_read(self):
        self.send_command({"cmd": "read"})

    def request_identify(self):
        self.send_command({"cmd": "identify"})

    def set_interval(self, ms):
        self.send_command({"cmd": "interval", "ms": ms})
```

**Usos**:
- Encapsulación de comandos al firmware Arduino
- Cola de comandos (extensible)
- Undo/Redo (potencial)

---

### 10. Template Method (Método Plantilla) — Comportamiento

**Ubicación**: `logic/serial_bridge.py` → `logic/bluetooth_bridge.py`

**Propósito**: Definir el esqueleto de un algoritmo en una operación, delegando pasos a subclases.

**Implementación**:
```python
class SerialBridge:
    def connect(self):
        self._serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        return True

class BluetoothBridge(SerialBridge):
    def connect(self):
        ok = super().connect()
        if ok:
            import time
            time.sleep(0.5)  # Paso específico de Bluetooth
        return ok
```

**Usos**:
- Conexión serial con pasos específicos por protocolo
- Extensible a otros protocolos que requieren inicialización especial

---

### 11. State (Estado) — Comportamiento

**Ubicación**: `domain/boards.py`

**Propósito**: Permitir que un objeto altere su comportamiento cuando su estado interno cambia.

**Implementación**:
```python
class Board:
    def __init__(self, board_id, conn="unknown", status="Desconectada", ...):
        self.id = board_id
        self.conn = conn
        self.status = status  # Estado: "Desconectada", "Conectada", "Error"

    def is_claimed(self):
        return self.usuario_id is not None

    def get_vendor_name(self):
        vendors = {
            0x0403: "FTDI",
            0x1A86: "WCH (CH340/CH341)",
            0x2341: "Arduino",
        }
        return vendors.get(self.vid, f"VID:{self.vid:04X}")
```

**Usos**:
- Cambio de comportamiento visual según estado de conexión
- Habilitación/deshabilitación de botones según estado
- Colores de indicadores de estado

---

## Patrones de Diseño Arquitectónicos

### 1. Layered Architecture (Arquitectura en Capas)

**Descripción**: Separación del sistema en capas horizontales con dependencias unidireccionales (de arriba hacia abajo).

**Capas del sistema**:

| Capa | Responsabilidad | Módulos |
|------|----------------|---------|
| **UI** | Interfaz gráfica, eventos de usuario | `ui/panels/`, `ui/dialogs/`, `ui/widgets/` |
| **Controller** | Adaptación UI-Servicio, validación de entrada | `controller/` |
| **Service** | Orquestación de lógica de negocio | `service/` |
| **Logic** | Protocolos de comunicación, procesamiento de datos | `logic/` |
| **Domain** | Entidades del negocio, reglas inmutables | `domain/` |
| **Data** | Persistencia, conexión a broker MQTT | `data/`, `connection/` |

**Regla de dependencia**: Las capas superiores dependen de las inferiores, nunca al revés.

---

### 2. Model-View-Controller (MVC) Adaptado

**Descripción**: Separación de datos (Model), interfaz (View) y lógica de control (Controller).

**Adaptación en FoT**:
- **Model**: `domain/` (Board, User, ConfigSnapshot) + `data/` (Database)
- **View**: `ui/` (paneles, widgets, diálogos)
- **Controller**: `controller/` (adaptadores entre View y Service)
- **Service Layer**: Capa adicional entre Controller y Logic para orquestación

**Flujo**:
```
Usuario → View → Controller → Service → Logic → Model → Database
   ↑___________________________________________________________|
                        (Observer para actualizaciones)
```

---

### 3. Repository Pattern (Patrón Repositorio)

**Descripción**: Abstracción de la capa de acceso a datos, desacoplando la lógica de negocio de la tecnología de persistencia.

**Implementación**: `data/database.py` actúa como repositorio único para todas las entidades.

```python
class Database:
    # Usuarios
    def create_user(self, username, password_hash, role="user") -> int
    def get_user_by_username(self, username) -> dict | None
    def list_users(self) -> list[dict]

    # Boards
    def save_board(self, board: dict) -> None
    def get_board_by_id(self, board_id) -> dict | None

    # Lecturas
    def save_reading(self, board_id, sensor_type, valor, unidad, ...)
    def get_readings(self, board_id, sensor_type=None, limit=100)

    # Eventos
    def save_event(self, board_id, tipo, descripcion)
    def get_events(self, board_id=None, limit=50)

    # Snapshots
    def save_snapshot(self, usuario_id, descripcion, datos_json)
    def get_snapshots(self, usuario_id=None) -> list[dict]
```

---

### 4. Event-Driven Architecture (Arquitectura Orientada a Eventos)

**Descripción**: Componentes reaccionan a eventos en lugar de llamadas directas, desacoplando emisores y receptores.

**Eventos en el sistema**:
- **MQTT Events**: `fot/+/sensores`, `fot/+/estado`
- **UI Events**: Board updated, Event logged, Sensor reading
- **System Events**: USB connected/disconnected, Bluetooth found, WiFi found

**Implementación**:
```python
# Emisor
class MQTTEventBus:
    def _on_message(self, client, userdata, message):
        data = json.loads(message.payload)
        self._notify(message.topic, data)

# Receptor (Observer)
class DataReceiver:
    def on_event(self, topic, data):
        # Procesa datos de sensores
        pass

class WiFiBridge:
    def on_event(self, topic, data):
        # Recibe datos MQTT como si fuera serial
        pass
```

---

### 5. Plugin Architecture (Arquitectura de Plugins)

**Descripción**: El sistema identifica automáticamente el tipo de sketch/sensor y adapta el comportamiento.

**Implementación**:
```python
def on_sensor_identify(self, board_id, data):
    board = self._boards.get(board_id)
    if not board:
        return
    board.sketch_id = data.get("sketch")      # "dht11", "soil", etc.
    board.sketch_name = data.get("name")
    board.sketch_version = data.get("version")
    # El panel DHT11 se activa automáticamente si sketch_id == "dht11"
```

**Extensibilidad**: Agregar un nuevo sensor solo requiere:
1. Nuevo sketch Arduino con `{"sketch": "nuevo_sensor"}`
2. Nuevo panel en `ui/panels/`
3. Registro en `MainWindow._build_layout()`

---

## Estructura de Carpetas

```
station/
├── bootstrap.py              # Verificación de entorno y setup inicial
├── main.py                   # Punto de entrada, wiring de dependencias
│
├── connection/               # Infraestructura de comunicación
│   ├── __init__.py
│   └── mqtt_client.py        # MQTTEventBus (Observer + Adapter)
│
├── controller/               # Adaptadores UI-Servicio (MVC Controller)
│   ├── auth_controller.py
│   ├── bluetooth_controller.py
│   ├── board_controller.py
│   ├── event_controller.py
│   ├── export_controller.py
│   ├── snapshot_controller.py
│   └── wifi_controller.py
│
├── data/                     # Capa de persistencia (Repository)
│   ├── __init__.py
│   └── database.py           # SQLite, acceso a datos
│
├── domain/                   # Entidades del negocio (MVC Model)
│   ├── __init__.py
│   ├── boards.py             # Board entity
│   ├── memento.py            # ConfigSnapshot, ConfigManager
│   └── user.py               # User, Role entities
│
├── help/                     # Documentación de usuario
│   └── help_text.py
│
├── logic/                    # Lógica de negocio y protocolos
│   ├── bluetooth_bridge.py   # Bridge para Bluetooth (Bridge pattern)
│   ├── data_receiver.py      # Procesamiento de datos de sensores
│   ├── db_verifier.py        # Verificación de escrituras
│   ├── device_scanner.py     # USBScanner (hilo daemon)
│   ├── exporter.py           # DataExporter (Strategy pattern)
│   ├── firmware_uploader.py  # Carga de firmware con avrdude
│   ├── __init__.py
│   ├── sensor_manager.py     # SensorManager (Facade pattern)
│   ├── serial_bridge.py      # SerialBridge (Bridge pattern)
│   └── wifi_bridge.py        # WiFiBridge (Adapter pattern)
│
├── service/                  # Orquestación de casos de uso
│   ├── auth_service.py       # Autenticación y autorización
│   ├── bluetooth_service.py
│   ├── board_service.py      # Gestión de placas (Factory Method)
│   ├── event_service.py
│   ├── export_service.py
│   ├── snapshot_service.py   # Memento pattern
│   └── wifi_service.py
│
└── ui/                       # Interfaz gráfica (MVC View)
    ├── dialogs/              # Ventanas modales
    │   ├── assign_arduino_dialog.py
    │   ├── bluetooth_scan_dialog.py
    │   ├── export_dialog.py
    │   ├── firmware_dialog.py
    │   ├── __init__.py
    │   ├── login_dialog.py
    │   ├── register_dialog.py
    │   └── wifi_scan_dialog.py
    ├── error_handler.py      # Manejo centralizado de errores
    ├── __init__.py
    ├── main_window.py          # Ventana principal, orquestador UI
    ├── panels/               # Paneles principales
    │   ├── admin_panel.py
    │   ├── arduino_panel.py
    │   ├── dht11_panel.py
    │   ├── help_panel.py
    │   ├── __init__.py
    │   ├── login_panel.py
    │   └── settings_panel.py
    ├── theme.py              # Configuración visual y constantes
    └── widgets/              # Componentes reutilizables
        ├── board_list.py
        ├── event_log.py
        ├── __init__.py
        ├── notification_manager.py  # Singleton + Observer
        ├── notification_panel.py
        ├── sensor_chart.py
        ├── side_bar.py
        ├── status_bar.py
        └── top_bar.py
```

---

## Diagrama de Capas Detallado

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  CTkFrame (customtkinter)                                   │   │
│  │  ├── Panels: DHT11Panel, ArduinoPanel, AdminPanel, ...     │   │
│  │  ├── Dialogs: LoginDialog, ExportDialog, FirmwareDialog    │   │
│  │  ├── Widgets: SideBar, TopBar, StatusBar, EventLog          │   │
│  │  └── Theme: apply_theme(), COLORS, FONT_*                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                         CAPA DE CONTROL                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AuthController  ──► valida credenciales, gestiona sesión   │   │
│  │  BoardController ──► conecta UI con operaciones de placas   │   │
│  │  EventController ──► maneja log de eventos                  │   │
│  │  ExportController ──► coordina exportación de datos         │   │
│  │  SnapshotController ──► gestiona snapshots de config        │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                         CAPA DE SERVICIO                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AuthService  ──► reglas de auth, hash de passwords         │   │
│  │  BoardService ──► registro, conexión, estado de placas      │   │
│  │  EventService ──► logging centralizado                    │   │
│  │  ExportService ──► orquesta exportación CSV/JSON            │   │
│  │  SnapshotService ──► crea/restaura snapshots (Memento)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      CAPA DE LÓGICA DE NEGOCIO                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SensorManager ──► Facade: unifica USB/BT/WiFi              │   │
│  │  SerialBridge  ──► Bridge: comunicación USB serial          │   │
│  │  BluetoothBridge ──► Bridge: extensión para Bluetooth       │   │
│  │  WiFiBridge    ──► Adapter: MQTT como interfaz serial       │   │
│  │  DataReceiver  ──► procesa y persiste lecturas            │   │
│  │  DataExporter  ──► Strategy: exporta CSV/JSON               │   │
│  │  FirmwareUploader ──► carga firmware con avrdude            │   │
│  │  USBScanner    ──► hilo daemon para auto-detección         │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                         CAPA DE DOMINIO                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Board ──► entidad: id, conn, status, sketch, factory data  │   │
│  │  User  ──► entidad: id, username, role, is_active         │   │
│  │  ConfigSnapshot ──► estado inmutable para Memento         │   │
│  │  ConfigManager  ──► crea/restaura snapshots               │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      CAPA DE INFRAESTRUCTURA                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Database ──► SQLite: usuarios, boards, lecturas, eventos   │   │
│  │  MQTTEventBus ──► Observer + pub/sub con paho-mqtt        │   │
│  │  Bootstrap ──► setup de Mosquitto, systemd, avrdude         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Flujo de Datos

### Lectura de Sensor (USB)
```
Arduino ──[JSON serial]──► SerialBridge._read_loop()
                              │
                              ▼
                    SerialBridge._process_line()
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            _on_reading()        _on_cmd_response()
                    │                   │
                    ▼                   ▼
            SensorManager         SensorManager
            (on_reading cb)       (on_identify cb)
                    │                   │
                    ▼                   ▼
            DataReceiver         BoardService
            .on_reading()        .on_sensor_identify()
                    │                   │
                    ▼                   ▼
            Database          Database
            .save_reading()    .save_board()
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    MQTTEventBus (Observer)
                    ._notify()
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              DHT11Panel          ArduinoPanel
              .update_reading()   .update_board()
```

### Lectura de Sensor (WiFi/MQTT)
```
Arduino UNO R4 ──[MQTT]──► Mosquitto Broker
                                │
                                ▼
                        MQTTEventBus._on_message()
                                │
                                ▼
                        MQTTEventBus._notify()
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              WiFiBridge                DataReceiver
              .on_event()              .on_event()
                    │                       │
                    ▼                       ▼
              _on_reading()           .on_reading()
                    │                       │
                    ▼                       ▼
              SensorManager             Database
              (callback)                .save_reading()
                    │
                    ▼
              DHT11Panel / ArduinoPanel
```

---

## Tecnologías y Dependencias

### Core
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Python | 3.10+ | Lenguaje principal |
| customtkinter | Latest | UI moderna con tema oscuro |
| tkinter | Built-in | Base de widgets |
| SQLite3 | Built-in | Base de datos embebida |

### Comunicación
| Tecnología | Propósito |
|------------|-----------|
| pyserial | Comunicación serial USB/Bluetooth |
| paho-mqtt | Cliente MQTT para WiFi |
| mosquitto | Broker MQTT local |

### Hardware
| Tecnología | Propósito |
|------------|-----------|
| avrdude | Carga de firmware Arduino |
| serial.tools.list_ports | Detección de puertos USB |

### Opcionales
| Tecnología | Propósito |
|------------|-----------|
| zeroconf | Descubrimiento mDNS de placas WiFi |
| bcrypt | Hash seguro de contraseñas |
| matplotlib | Gráficos de sensores (SensorChart) |

### Sistema Operativo
- **Primario**: Linux (Arch, Debian, Ubuntu)
- **Servicios**: systemd (user service)
- **Configuración**: `~/.config/fot/`

---

## Glosario de Términos

| Término | Definición |
|---------|------------|
| **Sketch** | Programa cargado en el Arduino |
| **Board / Placa** | Dispositivo Arduino físico |
| **Parcela** | Identificador lógico de una ubicación de monitoreo |
| **Sensor** | Periférico que mide magnitudes (temperatura, humedad) |
| **Lectura** | Valor actual capturado por un sensor |
| **Broker MQTT** | Servidor de mensajes Mosquitto que enruta datos |
| **Bridge** | Adaptador de protocolo de comunicación |
| **Snapshot** | Copia de seguridad de la configuración del sistema |
| **VID/PID** | Vendor ID / Product ID del chip USB |
| **RFCOMM** | Protocolo serial sobre Bluetooth |

---

## Conclusiones

Farm of Things demuestra una aplicación práctica de múltiples patrones de diseño GoF y arquitectónicos para resolver un problema real de IoT:

1. **Bridge + Adapter** permiten soportar múltiples protocolos de comunicación (USB, Bluetooth, WiFi) con una interfaz unificada.

2. **Observer** desacopla la recepción de datos de su procesamiento y visualización.

3. **Layered Architecture** garantiza mantenibilidad y testabilidad.

4. **Memento + Strategy** añaden funcionalidades avanzadas (snapshots, exportación) sin romper la arquitectura existente.

5. **Singleton** asegura consistencia en el sistema de notificaciones.

6. **Facade** simplifica la interacción con subsistemas complejos de comunicación.

El diseño está preparado para extensión: nuevos sensores, protocolos o formatos de exportación pueden agregarse respetando las interfaces existentes y los principios SOLID.

---

*Documento generado para el proyecto Farm of Things (FoT) — Estación Base IoT*
*Arquitectura: Layered + MVC + Event-Driven*
*Patrones GoF: Observer, Singleton, Strategy, Bridge, Adapter, Facade, Factory Method, Memento, Command, Template Method, State*
