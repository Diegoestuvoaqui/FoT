# FoT — Plan de Programación por Capas

> Documento de referencia para la implementación del sistema Farm of Things. Cada tarea está descrita al nivel de lo que debe existir en el código, no solo lo que hace.

---

## Índice

- [[#Capa 1 — Nodo de Campo (Arduino UNO R3, C++)]]
    - [[#1.1 Abstracción de sensores]]
    - [[#1.2 Máquina de estados (FSM)]]
    - [[#1.3 Persistencia en EEPROM (Memento)]]
    - [[#1.4 Autenticación RFID (RC522)]]
    - [[#1.5 Cliente MQTT (PubSubClient)]]
    - [[#1.6 Control del relay]]
    - [[#1.7 Watchdog timer]]
- [[#Capa 2 — Comunicación (Eclipse Mosquitto)]]
    - [[#2.1 Instalación y archivo de configuración]]
    - [[#2.2 Esquema de tópicos y formato de mensajes]]
    - [[#2.3 Arranque automático del broker]]
- [[#Capa 3 — Estación Base (Python 3 + SQLite)]]
    - [[#3.1 Modelo de dominio (Composite)]]
    - [[#3.2 Base de datos SQLite]]
    - [[#3.3 Motor de eventos MQTT (Observer)]]
    - [[#3.4 Motor de decisión de riego]]
    - [[#3.5 Snapshot de configuración (Memento)]]
    - [[#3.6 Interfaz gráfica (Tkinter)]]
    - [[#3.7 Arranque automático de la aplicación]]
- [[#Orden de implementación recomendado]]
- [[#Dependencias entre tareas]]

---

## Capa 1 — Nodo de Campo (Arduino UNO R3, C++)

**Lenguaje:** C++  
**Entorno:** Arduino IDE 2.x o PlatformIO  
**Hardware objetivo:** Arduino UNO R3 + módulo RC522 + DHT22 + sensor capacitivo de humedad de suelo + relay  
**Bibliotecas necesarias:**

- `DHT sensor library` (Adafruit) — lectura del DHT22
- `MFRC522` — comunicación SPI con el módulo RC522
- `PubSubClient` — cliente MQTT sobre TCP
- `EEPROM.h` — incluida en el núcleo de Arduino
- `avr/wdt.h` — watchdog timer del ATmega328P

---

### 1.1 Abstracción de sensores

**Patrón:** Adapter + Abstract Factory  
**Archivos a crear:** `ISensor.h`, `DHT22Adapter.h/.cpp`, `SoilMoistureAdapter.h/.cpp`, `SensorFactory.h/.cpp`

**Qué debe existir exactamente:**

#### `ISensor.h`

- Clase abstracta (o interfaz pura) con los siguientes métodos virtuales puros:
    - `float read()` — devuelve la lectura principal del sensor en su unidad natural (°C para temperatura, % para humedad).
    - `bool isValid()` — devuelve `true` si la última lectura está dentro del rango operativo del sensor. Para el DHT22: temperatura entre -40 y 80 °C, humedad entre 0 y 100 %. Para el sensor capacitivo: valor ADC entre 0 y 1023.
    - `String getUnit()` — devuelve la cadena de unidad ("%" o "°C") para serialización MQTT.
    - `String getSensorType()` — devuelve un identificador de tipo ("DHT22_TEMP", "DHT22_HUM", "SOIL_CAP").
- Destructor virtual vacío.

#### `DHT22Adapter.h/.cpp`

- Hereda de `ISensor`.
- Constructor recibe: `uint8_t pin` (pin de datos del DHT22) y `uint8_t readingType` (constante que indica si esta instancia lee temperatura o humedad, porque el DHT22 entrega ambas pero se necesitan dos objetos `ISensor` separados).
- Internamente crea e inicializa un objeto `DHT dht(pin, DHT22)`.
- `read()` llama a `dht.readTemperature()` o `dht.readHumidity()` según `readingType`.
- `isValid()` comprueba que el valor retornado por `read()` no sea `NaN` y esté dentro de rango.
- Debe manejar el caso en que el DHT22 no responde (retorna `NaN`): en ese caso `isValid()` devuelve `false` y la FSM debe transitar a estado `Fault`.

#### `SoilMoistureAdapter.h/.cpp`

- Hereda de `ISensor`.
- Constructor recibe: `uint8_t analogPin`.
- `read()` llama a `analogRead(analogPin)` y mapea el valor crudo (0–1023) a porcentaje de humedad (0–100 %) mediante `map()`. El mapeo debe ser configurable: los valores de "seco total" y "saturado" se pasan al constructor como `int dryValue` y `int wetValue` para permitir calibración por parcela.
- `isValid()` verifica que el valor ADC crudo no sea 0 ni 1023 (valores que indican sensor desconectado).

#### `SensorFactory.h/.cpp`

- Clase estática o con método de fábrica: `static ISensor* create(String sensorType, uint8_t pin, ...)`.
- Recibe como primer parámetro el tipo de sensor como cadena ("DHT22_TEMP", "DHT22_HUM", "SOIL_CAP") y devuelve un puntero a la instancia del adaptador correspondiente.
- Si el tipo no es reconocido, devuelve `nullptr` y el sistema debe registrar un fallo.
- Permite agregar nuevos sensores (pH, salinidad) en el futuro añadiendo solo un nuevo `case` y un nuevo adaptador, sin tocar el resto del código.

---

### 1.2 Máquina de estados (FSM)

**Patrón:** State  
**Archivos a crear:** `IState.h`, `StateIdle.h/.cpp`, `StateMonitoring.h/.cpp`, `StateIrrigating.h/.cpp`, `StateFault.h/.cpp`, `StateMachine.h/.cpp`

**Qué debe existir exactamente:**

#### `IState.h`

- Clase abstracta con método virtual puro `void handle(StateMachine& ctx)`.
- El parámetro `ctx` es una referencia al contexto (la máquina de estados) que el estado puede leer (sensores, umbrales) y modificar (cambiar al siguiente estado, activar relay).

#### `StateMachine.h/.cpp`

- Contiene el estado actual como puntero a `IState`.
- Expone métodos:
    - `void setState(IState* newState)` — cambia el estado actual y libera el anterior.
    - `void tick()` — llama a `currentState->handle(*this)` en cada iteración del `loop()`.
    - `void setRelay(bool on)` — activa o desactiva el pin digital del relay.
    - `float getHumidity()` — retorna la última lectura del sensor capacitivo.
    - `float getTemperature()` — retorna la última lectura del DHT22.
    - `float getHumidityThreshold()` — retorna el umbral mínimo de humedad cargado desde EEPROM.
    - `bool isFarmerAuthenticated()` — retorna si el RFID fue validado en la sesión actual.
- También guarda las instancias de los sensores (obtenidas de `SensorFactory`) y el pin del relay.

#### `StateIdle`

- Estado inicial y de espera. El relay está apagado.
- `handle()`: lee el RFID en cada tick. Si el Farmer se autentica (`ctx.isFarmerAuthenticated()`), transita a `StateMonitoring` si el modo guardado en EEPROM es automático, o permanece en `Idle` esperando comando manual.
- No realiza lecturas de sensores para ahorrar energía.

#### `StateMonitoring`

- El sistema lee sensores periódicamente (cada N segundos, configurable desde EEPROM).
- `handle()`: lee humedad del suelo. Si `humedad < umbralMinimo`, transita a `StateIrrigating`. Si cualquier sensor reporta `isValid() == false`, transita a `StateFault`. En caso contrario, publica lectura por MQTT y permanece en `Monitoring`.
- Debe acumular lecturas consecutivas inválidas antes de declarar `Fault` (p.ej. 3 lecturas inválidas seguidas) para evitar falsos positivos.

#### `StateIrrigating`

- El relay está encendido (bomba activa).
- `handle()`: sigue leyendo humedad. Cuando `humedad >= umbralMaximo` (umbral de saturación), apaga el relay y transita a `StateMonitoring`. Si se supera un tiempo máximo de irrigación configurable (guardado en EEPROM, p.ej. 300 segundos), apaga el relay y transita a `StateFault` para evitar inundación por fallo de sensor.
- Publica su estado en el tópico MQTT de estado en cada cambio.

#### `StateFault`

- El relay está apagado de forma forzada.
- `handle()`: publica el error por MQTT (tipo de fallo: sensor inválido, timeout de irrigación). Espera un comando externo de reset enviado por MQTT, o un reset físico (watchdog).
- No intenta reanudar la operación por sí solo.

---

### 1.3 Persistencia en EEPROM (Memento)

**Patrón:** Memento  
**Archivo a crear:** `EEPROMConfig.h/.cpp`

**Qué debe existir exactamente:**

#### Estructura de datos a persistir

Definir un `struct ConfigData` que contenga:

- `float humidityThresholdMin` — umbral mínimo de humedad para activar riego (%).
- `float humidityThresholdMax` — umbral de saturación para detener riego (%).
- `uint16_t irrigationTimeoutSec` — tiempo máximo de riego antes de pasar a Fault.
- `uint16_t monitoringIntervalSec` — intervalo entre lecturas en modo Monitoring.
- `uint8_t operationMode` — 0 = manual, 1 = automático.
- `uint8_t rfidUID[4]` — los 4 bytes del UID de la tarjeta RFID autorizada.
- `uint8_t checksum` — byte de verificación de integridad (XOR de todos los campos anteriores).

#### `EEPROMConfig.h/.cpp`

- `void save(const ConfigData& cfg)` — serializa el struct y lo escribe en la EEPROM comenzando en la dirección 0. Calcula y escribe el checksum al final.
- `bool load(ConfigData& cfg)` — lee el struct desde EEPROM, recalcula el checksum y lo compara. Si no coincide (primera ejecución o datos corruptos), carga valores por defecto seguros y retorna `false` para que el sistema lo registre como aviso.
- `void writeDefaults(ConfigData& cfg)` — rellena el struct con valores por defecto seguros: umbralMin=30%, umbralMax=70%, timeoutSec=300, intervaloSec=60, modo=manual, UID={0,0,0,0}.

**Por qué importa el checksum:** si hay un corte eléctrico durante una escritura en EEPROM, el struct puede quedar corrupto. El checksum detecta esto y evita que el sistema arranque con configuración basura.

---

### 1.4 Autenticación RFID (RC522)

**Patrón:** ninguno GoF específico; usa EEPROM para persistencia  
**Biblioteca:** `MFRC522`  
**Archivo a crear:** `RFIDAuth.h/.cpp`

**Qué debe existir exactamente:**

#### Conexión hardware del RC522 con el UNO R3

El módulo RC522 usa SPI. Las conexiones físicas fijas son:

- SDA (SS) → pin 10
- SCK → pin 13
- MOSI → pin 11
- MISO → pin 12
- RST → pin 9
- VCC → 3.3V (¡no 5V, el RC522 es de 3.3V!)
- GND → GND

Estas conexiones deben estar documentadas en comentario al inicio del archivo principal `.ino`.

#### `RFIDAuth.h/.cpp`

- Constructor: recibe `uint8_t ssPin`, `uint8_t rstPin`.
- `void begin()` — inicializa SPI y crea el objeto `MFRC522 mfrc522(ssPin, rstPin)`. Llama a `mfrc522.PCD_Init()`.
- `bool isCardPresent()` — retorna `true` si hay una tarjeta en el campo (`mfrc522.PICC_IsNewCardPresent()` y `mfrc522.PICC_ReadCardSerial()`).
- `bool authenticate(const uint8_t* storedUID, uint8_t uidLength)` — compara el UID leído con el UID almacenado en EEPROM byte a byte. Retorna `true` solo si todos los bytes coinciden. El UID del RC522 típicamente son 4 bytes (`mfrc522.uid.uidByte[0..3]`).
- `void getUID(uint8_t* buffer)` — copia el UID de la última lectura a un buffer de 4 bytes.
- `void enrollNewCard(ConfigData& cfg)` — lee el UID de la tarjeta presente y lo guarda en `cfg.rfidUID`. Luego llama a `EEPROMConfig::save()`. Solo debe ser invocable desde un estado privilegiado (p.ej. desde `StateIdle` cuando hay una combinación especial de botón físico).
- Llamar a `mfrc522.PICC_HaltA()` al terminar cada lectura para evitar lecturas dobles.

---

### 1.5 Cliente MQTT (PubSubClient)

**Biblioteca:** `PubSubClient`  
**Requiere:** una conexión de red activa (WiFi con `WiFiClient`, o adaptación para módulo LoRa/RF433 con capa de transporte personalizada)  
**Archivo a crear:** `MQTTClient.h/.cpp`

**Qué debe existir exactamente:**

#### Tópicos a publicar desde el Arduino

- `fot/<parcela>/sensores` — payload JSON con lecturas actuales.
- `fot/<parcela>/estado` — payload JSON con el estado actual de la FSM.

#### Tópicos a los que suscribirse

- `fot/<parcela>/control` — recibe comandos de la estación base (p.ej. `{"cmd":"irrigate"}`, `{"cmd":"stop"}`, `{"cmd":"reset_fault"}`).

#### `MQTTClient.h/.cpp`

- Constructor: recibe `Client& networkClient` (para poder intercambiar el cliente de red sin cambiar esta clase), `const char* brokerIP`, `uint16_t brokerPort`, `const char* parcelaId`.
- `void begin()` — configura el servidor y el callback con `pubSubClient.setServer(...)` y `pubSubClient.setCallback(onMessage)`.
- `bool connect()` — intenta conectar con ID de cliente derivado de `parcelaId`. Si falla, reintenta hasta 3 veces con espera de 2 segundos. Tras conectar, se suscribe a `fot/<parcelaId>/control` con QoS 1.
- `void loop()` — debe llamarse en cada iteración del `loop()` principal para mantener la conexión viva (`pubSubClient.loop()`). Si la conexión se perdió, reintenta `connect()`.
- `void publishSensorData(float humidity, float temperature)` — construye el JSON manualmente con `snprintf` (no usar `ArduinoJson` para no gastar memoria) y publica en `fot/<parcelaId>/sensores` con `retain=false`, QoS 1.
- `void publishState(const char* stateName)` — publica en `fot/<parcelaId>/estado`.
- Callback `onMessage(char* topic, byte* payload, unsigned int length)` — compara el tópico recibido, parsea el campo `"cmd"` del payload JSON manualmente (buscar la cadena con `strstr`, no usar librerías de parsing) y llama a la función de despacho de la FSM.

**Por qué parseo manual de JSON:** `ArduinoJson` consume aproximadamente 1–2 KB de RAM adicional. El ATmega328P tiene solo 2 KB de SRAM total. El formato de comandos es simple y predecible, lo que hace viable el parseo con `strstr`.

---

### 1.6 Control del relay

**Archivo:** lógica distribuida en `StateMachine.cpp` y los estados  
**No requiere clase propia**

**Qué debe existir exactamente:**

- Definir la constante `RELAY_PIN` en el archivo principal `.ino` (p.ej. pin 7).
- El relay de los módulos de 1 canal comunes en el mercado cubano es activo en bajo: escribir `LOW` en el pin activa la bobina. Esto debe estar documentado con un comentario y manejado con una constante: `#define RELAY_ON LOW` y `#define RELAY_OFF HIGH`.
- `StateMachine::setRelay(bool on)` llama a `digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF)`.
- Solo `StateIrrigating` puede llamar a `setRelay(true)`. Todos los demás estados garantizan que el relay esté apagado en su método `handle()` antes de cualquier otra acción. Esto evita que el relay quede encendido si hay una transición de estado inesperada.

---

### 1.7 Watchdog timer

**Archivo:** `main.ino` (configuración inicial) y dentro de `loop()`

**Qué debe existir exactamente:**

- Al inicio de `setup()`, activar el watchdog con un timeout de 8 segundos (el máximo del ATmega328P): `wdt_enable(WDTO_8S)`.
- Al final de cada iteración del `loop()` principal, resetear el watchdog: `wdt_reset()`.
- Si el `loop()` se bloquea por más de 8 segundos (cuelgue de la red, sensor bloqueado), el microcontrolador se reinicia automáticamente.
- Después del reinicio, `setup()` carga la configuración desde EEPROM (mediante `EEPROMConfig::load()`) y la FSM arranca en `StateIdle`. Esto implementa RES-10 sin intervención del Farmer.
- **Precaución:** no llamar a `wdt_reset()` dentro de interrupciones ni después de `delay()` largo. Usar `millis()` para temporización no bloqueante en todo el código.

---

## Capa 2 — Comunicación (Eclipse Mosquitto)

**No se escribe código propio en esta capa.** Se configura un servicio existente.  
**Sistema operativo objetivo:** Linux (primario) y Windows (secundario)

---

### 2.1 Instalación y archivo de configuración

**Archivo a crear/editar:** `/etc/mosquitto/mosquitto.conf` (Linux) o `C:\mosquitto\mosquitto.conf` (Windows)

**Qué debe contener el archivo de configuración:**

```
# Puerto estándar MQTT
listener 1883

# Permitir conexiones solo desde la red local (no exponer a Internet)
# bind_address 192.168.X.X   ← descomentar y ajustar a la IP local del Farmer

# Para desarrollo sin autenticación (cambiar en producción)
allow_anonymous true

# Deshabilitar persistencia de sesión si no se necesita historial de mensajes
# persistence false

# Log de errores (útil para depuración en campo)
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
```

**Por qué `allow_anonymous true` es aceptable aquí:** el broker escucha solo en la red local de la finca (sin acceso a Internet por RES-09). No hay servicios externos que puedan conectarse. En un despliegue final se puede agregar autenticación con usuario/contraseña usando `password_file`.

**Verificación del funcionamiento:**

- Abrir dos terminales. En la primera: `mosquitto_sub -h localhost -t fot/# -v`
- En la segunda: `mosquitto_pub -h localhost -t fot/parcela1/sensores -m '{"hum":55.2,"temp":28.1}'`
- Si aparece el mensaje en la primera terminal, el broker funciona correctamente.

---

### 2.2 Esquema de tópicos y formato de mensajes

**Documento de referencia** (no código): definir y mantener este esquema como fuente de verdad para ambas capas.

#### Tópicos definidos

|Tópico|Dirección|Publicado por|Suscrito por|
|---|---|---|---|
|`fot/<parcela>/sensores`|Arduino → Base|Arduino|Estación base|
|`fot/<parcela>/estado`|Arduino → Base|Arduino|Estación base|
|`fot/<parcela>/control`|Base → Arduino|Estación base|Arduino|

`<parcela>` es un identificador corto sin espacios, p.ej. `p1`, `p2`, `norte`, `sur`.

#### Formato JSON de cada tópico

**`fot/<parcela>/sensores`**

```json
{
  "hum_suelo": 42.5,
  "hum_aire": 65.0,
  "temp": 28.3,
  "ts": 1700000000
}
```

- `hum_suelo`: humedad del suelo en % (sensor capacitivo).
- `hum_aire`: humedad relativa del ambiente en % (DHT22).
- `temp`: temperatura del aire en °C (DHT22).
- `ts`: timestamp Unix en segundos. El Arduino UNO no tiene RTC, así que este campo puede ser 0 o un contador de segundos desde el arranque. La estación base aplicará el timestamp real al recibirlo.

**`fot/<parcela>/estado`**

```json
{
  "state": "Monitoring",
  "relay": false,
  "uptime": 3600
}
```

- `state`: cadena con el nombre del estado actual ("Idle", "Monitoring", "Irrigating", "Fault").
- `relay`: `true` si la bomba está activa.
- `uptime`: segundos desde el último reinicio del Arduino.

**`fot/<parcela>/control`**

```json
{
  "cmd": "irrigate"
}
```

- Valores posibles de `cmd`: `"irrigate"` (activa riego manual), `"stop"` (detiene riego), `"reset_fault"` (intenta recuperación desde Fault), `"set_mode_auto"`, `"set_mode_manual"`.

---

### 2.3 Arranque automático del broker

**Linux (systemd) — verificar que el servicio esté habilitado:**

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto   # debe mostrar "active (running)"
```

**Windows — Tarea Programada:**

- Crear una tarea que ejecute `C:\mosquitto\mosquitto.exe -c C:\mosquitto\mosquitto.conf` con el disparador "Al iniciar el sistema", bajo cuenta de sistema, sin importar si hay usuario conectado.

---

## Capa 3 — Estación Base (Python 3 + SQLite)

**Lenguaje:** Python 3.8+  
**Bibliotecas necesarias (todas incluidas en stdlib o instalables con pip sin licencia):**

- `paho-mqtt` — cliente MQTT.
- `sqlite3` — incluida en Python stdlib.
- `tkinter` — incluida en Python stdlib (en Linux puede requerir `python3-tk`).
- `json` — incluida en stdlib.
- `threading` — incluida en stdlib.
- `datetime` — incluida en stdlib.

**Estructura de archivos sugerida:**

```
estacion_base/
├── main.py                  ← punto de entrada
├── domain/
│   ├── __init__.py
│   ├── components.py        ← Composite (IComponente, Finca, Parcela, Dispositivo)
│   └── memento.py           ← Memento de configuración
├── data/
│   ├── __init__.py
│   ├── database.py          ← SQLite DAO
│   └── fot.db               ← archivo de base de datos (generado en runtime)
├── mqtt/
│   ├── __init__.py
│   └── mqtt_client.py       ← Subject del patrón Observer
├── logic/
│   ├── __init__.py
│   └── decision_engine.py   ← motor de decisión (Observer)
└── ui/
    ├── __init__.py
    └── main_window.py       ← interfaz Tkinter (Observer)
```

---

### 3.1 Modelo de dominio (Composite)

**Patrón:** Composite  
**Archivo:** `domain/components.py`

**Qué debe existir exactamente:**

#### Clase abstracta `IComponente`

- Método abstracto `get_id() -> str` — identificador único del componente.
- Método abstracto `get_name() -> str` — nombre legible.
- Método abstracto `get_latest_reading() -> dict` — retorna el último dato disponible como diccionario.
- Método abstracto `get_children() -> list` — retorna lista de hijos (vacía para hojas).
- Método `apply(operation: callable)` — aplica una función a este componente y recursivamente a todos sus hijos. Permite, por ejemplo, obtener todas las lecturas de toda la finca con una sola llamada.

#### Clase `Dispositivo` (hoja del árbol)

- Implementa `IComponente`.
- Atributos: `id`, `name`, `parcela_id`, `tipo` ("sensor" o "actuador"), `last_reading: dict`.
- `get_children()` retorna lista vacía.
- `update_reading(data: dict)` — actualiza `last_reading` con los datos recibidos por MQTT.
- `get_latest_reading()` retorna `last_reading`.

#### Clase `Parcela` (nodo intermedio)

- Implementa `IComponente`.
- Atributos: `id`, `name`, `umbral_min: float`, `umbral_max: float`, `modo: str` ("auto" o "manual"), `dispositivos: list[Dispositivo]`.
- `add_device(d: Dispositivo)` y `remove_device(device_id: str)`.
- `get_children()` retorna `dispositivos`.
- `get_latest_reading()` agrega las lecturas de todos sus dispositivos en un solo dict.

#### Clase `Finca` (raíz del árbol)

- Implementa `IComponente`.
- Atributos: `id`, `name`, `parcelas: list[Parcela]`.
- `add_parcela(p: Parcela)` y `remove_parcela(parcela_id: str)`.
- `get_parcela(parcela_id: str) -> Parcela` — búsqueda por ID.
- `get_children()` retorna `parcelas`.
- `get_all_readings() -> list[dict]` — usa `apply()` para recopilar lecturas de toda la finca.

---

### 3.2 Base de datos SQLite

**Patrón:** DAO (Data Access Object)  
**Archivo:** `data/database.py`

**Esquema de tablas:**

```sql
CREATE TABLE IF NOT EXISTS parcelas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    umbral_min REAL DEFAULT 30.0,
    umbral_max REAL DEFAULT 70.0,
    modo TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dispositivos (
    id TEXT PRIMARY KEY,
    parcela_id TEXT NOT NULL REFERENCES parcelas(id),
    name TEXT NOT NULL,
    tipo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lecturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcela_id TEXT NOT NULL,
    hum_suelo REAL,
    hum_aire REAL,
    temp REAL,
    ts_arduino INTEGER,
    ts_base TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcela_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descripcion TEXT,
    ts TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS configuracion_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion TEXT,
    datos_json TEXT NOT NULL,
    ts TEXT DEFAULT (datetime('now'))
);
```

**Clase `Database`:**

- Constructor: recibe `db_path: str`. Llama a `sqlite3.connect(db_path, check_same_thread=False)`. El argumento `check_same_thread=False` es necesario porque el hilo MQTT y el hilo de UI accederán a la base de datos concurrentemente.
- `initialize()` — ejecuta el script de creación de tablas si no existen.
- `save_reading(parcela_id: str, data: dict)` — inserta en `lecturas`. Extrae los campos del dict JSON recibido de MQTT.
- `save_event(parcela_id: str, tipo: str, descripcion: str)` — inserta en `eventos`.
- `get_readings(parcela_id: str, limit: int = 100) -> list[dict]` — retorna las últimas N lecturas de una parcela ordenadas por `ts_base DESC`.
- `get_parcelas() -> list[dict]` — retorna todas las parcelas con su configuración.
- `save_parcela(parcela: dict)` — inserta o actualiza (UPSERT) una parcela.
- `save_snapshot(descripcion: str, datos_json: str)` — guarda un snapshot de configuración.
- `get_snapshots() -> list[dict]` — lista todos los snapshots disponibles.
- Todos los métodos deben usar un `threading.Lock` para proteger el acceso concurrente a la conexión SQLite.

---

### 3.3 Motor de eventos MQTT (Observer)

**Patrón:** Observer (Subject)  
**Archivo:** `mqtt/mqtt_client.py`

**Qué debe existir exactamente:**

#### Clase `MQTTEventBus` (Subject)

- Atributos: `_observers: list` — lista de objetos que implementan el método `on_event(topic: str, data: dict)`.
- Constructor: recibe `broker_host: str`, `broker_port: int = 1883`.
- `register(observer)` — añade un observer a la lista.
- `unregister(observer)` — elimina un observer.
- `_notify(topic: str, data: dict)` — itera la lista de observers y llama a `observer.on_event(topic, data)` en cada uno. Si un observer lanza una excepción, la captura y la registra en el log sin detener la notificación a los demás.
- `start()` — crea el cliente `paho.mqtt.client.Client`, registra los callbacks `on_connect` y `on_message`, llama a `client.connect(broker_host, broker_port)` y arranca `client.loop_start()` (hilo de red en segundo plano, no bloqueante).
- `stop()` — llama a `client.loop_stop()` y `client.disconnect()`.
- Callback `on_connect(client, userdata, flags, rc)` — si `rc == 0` (éxito), suscribirse a `fot/+/sensores`, `fot/+/estado` con QoS 1. El comodín `+` captura cualquier ID de parcela.
- Callback `on_message(client, userdata, msg)` — decodifica el payload como JSON con `json.loads()`. Llama a `self._notify(msg.topic, data)`. Maneja la excepción `json.JSONDecodeError` registrando el error sin romper el hilo.
- `publish(topic: str, payload: dict)` — serializa el dict a JSON y llama a `client.publish(topic, json.dumps(payload), qos=1)`.

---

### 3.4 Motor de decisión de riego

**Patrón:** Observer (Observer concreto) + Strategy (para extensibilidad futura de algoritmos de decisión)  
**Archivo:** `logic/decision_engine.py`

**Qué debe existir exactamente:**

#### Clase `DecisionEngine`

- Implementa el método `on_event(topic: str, data: dict)` para actuar como Observer del `MQTTEventBus`.
- Constructor: recibe `mqtt_bus: MQTTEventBus`, `db: Database`, `finca: Finca`.
- `on_event(topic, data)`:
    - Extrae el ID de parcela del tópico con `topic.split('/')[1]`.
    - Si el tópico termina en `/sensores`:
        1. Obtiene la parcela del modelo de dominio: `parcela = finca.get_parcela(parcela_id)`.
        2. Guarda la lectura en la base de datos: `db.save_reading(parcela_id, data)`.
        3. Actualiza la lectura en el modelo de dominio.
        4. Si `parcela.modo == "auto"`:
            - Si `data['hum_suelo'] < parcela.umbral_min`: publica comando de riego: `mqtt_bus.publish(f'fot/{parcela_id}/control', {"cmd": "irrigate"})`. Registra el evento en la base de datos.
            - Si `data['hum_suelo'] >= parcela.umbral_max`: publica comando de parada: `mqtt_bus.publish(f'fot/{parcela_id}/control', {"cmd": "stop"})`. Registra el evento.
    - Si el tópico termina en `/estado`: actualiza el modelo de dominio con el estado recibido y registra en `eventos` si el estado es "Fault".
- La lógica de decisión debe ser reemplazable en el futuro por una estrategia más sofisticada (promedio de lecturas, programación horaria) sin cambiar el `DecisionEngine` — esto es la base del patrón Strategy para extensibilidad futura.

---

### 3.5 Snapshot de configuración (Memento)

**Patrón:** Memento  
**Archivo:** `domain/memento.py`

**Qué debe existir exactamente:**

#### Clase `ConfigSnapshot` (Memento)

- Almacena un snapshot inmutable de la configuración de la finca en un momento dado.
- Atributos: `_state: str` (JSON serializado de todas las parcelas), `_timestamp: str`.
- `get_state() -> str` — retorna el JSON almacenado.

#### Clase `ConfigManager` (Caretaker + Originator combinados para simplidad)

- `save_snapshot(finca: Finca, descripcion: str, db: Database)` — serializa la jerarquía completa de la finca a JSON, crea un `ConfigSnapshot` y lo persiste en la tabla `configuracion_snapshots` de SQLite.
- `list_snapshots(db: Database) -> list[dict]` — retorna la lista de snapshots disponibles con su ID, descripción y timestamp.
- `restore_snapshot(snapshot_id: int, db: Database) -> dict` — recupera el JSON del snapshot y lo deserializa a un dict que puede usarse para reconstruir la jerarquía de dominio.
- La UI debe llamar a `save_snapshot()` automáticamente antes de cualquier operación de edición de parcelas (añadir, eliminar, cambiar umbrales) para que el usuario siempre pueda deshacer.

---

### 3.6 Interfaz gráfica (Tkinter)

**Patrón:** Observer (Observer concreto)  
**Archivo:** `ui/main_window.py`

**Qué debe existir exactamente:**

#### Clase `MainWindow`

- Implementa `on_event(topic: str, data: dict)` para actuar como Observer del `MQTTEventBus`.
- Constructor: recibe `root: tk.Tk`, `finca: Finca`, `mqtt_bus: MQTTEventBus`, `db: Database`, `config_manager: ConfigManager`.

#### Estructura de la ventana principal

La ventana debe tener como mínimo tres secciones diferenciadas:

**Panel lateral izquierdo — árbol de parcelas:**

- `ttk.Treeview` que muestra la jerarquía `Finca → Parcela → Dispositivo`.
- Al seleccionar una parcela, el panel central se actualiza con sus datos.
- Botones: "Añadir parcela", "Eliminar parcela" (con confirmación), "Guardar snapshot".

**Panel central — datos de la parcela seleccionada:**

- Lectura actual: humedad del suelo, humedad del aire, temperatura (como etiquetas `tk.Label` que se actualizan en tiempo real).
- Estado actual de la FSM del Arduino (Idle / Monitoring / Irrigating / Fault) mostrado con color: verde para Monitoring, azul para Irrigating, rojo para Fault, gris para Idle.
- Umbrales configurados, editables con `ttk.Entry`. Botón "Aplicar" que guarda en base de datos y envía los nuevos umbrales al Arduino por MQTT (como un campo del tópico de control).
- Selector de modo (auto/manual) con `ttk.Combobox`.
- Botones de control manual: "Activar riego" y "Detener riego" (solo habilitados si el modo es manual).

**Panel inferior — log de eventos:**

- `tk.Text` en modo solo lectura que muestra los últimos eventos (irrigaciones, fallos, cambios de estado) con timestamp.

#### Actualización segura desde el hilo MQTT

- `on_event(topic, data)` se ejecuta en el hilo de red de paho-mqtt, no en el hilo principal de Tkinter.
- Llamar directamente a métodos de UI desde un hilo secundario corrompe Tkinter.
- Solución: `on_event()` no actualiza la UI directamente. En su lugar, llama a `self.root.after(0, self._update_ui, topic, data)`. El método `after(0, ...)` encola la llamada de actualización en el hilo principal de Tkinter para que se ejecute en la siguiente iteración del event loop.
- `_update_ui(topic, data)` sí puede modificar los widgets con seguridad.

---

### 3.7 Arranque automático de la aplicación

**Archivo a crear:** `estacion_base.service` (Linux) o instrucciones para Tarea Programada (Windows)

**Linux — servicio systemd:**

```ini
[Unit]
Description=FoT Estacion Base
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/farmer/estacion_base/main.py
WorkingDirectory=/home/farmer/estacion_base
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

La directiva `After=mosquitto.service` garantiza que el broker esté activo antes de que la aplicación Python intente conectarse. `Restart=on-failure` relanza la aplicación si termina inesperadamente.

---

## Orden de implementación recomendado

```
1. [C++]    ISensor + DHT22Adapter + SoilMoistureAdapter + SensorFactory
              → Prueba: leer sensores en el monitor serie sin más código.

2. [C++]    EEPROMConfig (load/save/defaults)
              → Prueba: guardar valores, apagar, encender, verificar que se leen los mismos.

3. [C++]    RFIDAuth (leer UID y comparar)
              → Prueba: imprimir UID en monitor serie al acercar tarjeta.

4. [Config] Instalar Mosquitto y verificar con mosquitto_sub / mosquitto_pub.

5. [C++]    FSM completa (sin MQTT aún, con relay simulado en LED)
              → Prueba: verificar transiciones de estado en monitor serie.

6. [C++]    MQTTClient sobre WiFi
              → Prueba: publicar lecturas y verificarlas con mosquitto_sub.

7. [Python] Database (esquema + DAO)
              → Prueba: insertar y leer registros desde un script de prueba.

8. [Python] IComponente + Finca + Parcela + Dispositivo
              → Prueba: construir jerarquía en memoria y recorrerla.

9. [Python] MQTTEventBus + DecisionEngine
              → Prueba: con Arduino enviando datos reales, verificar que la base de datos recibe lecturas.

10. [Python] MainWindow Tkinter (primero solo la visualización, luego el control)
              → Prueba: ver lecturas en tiempo real desde el Arduino.

11. [Python] ConfigManager (Memento)
              → Prueba: crear snapshot, modificar umbral, restaurar.

12. [Config] Arranque automático de Mosquitto y la aplicación Python.
```

---

## Dependencias entre tareas

|Tarea|Depende de|
|---|---|
|FSM (1.2)|ISensor (1.1)|
|EEPROM (1.3)|Ninguna|
|RFID (1.4)|EEPROM (1.3) — para leer/guardar UID|
|MQTTClient Arduino (1.5)|FSM (1.2), conexión de red activa|
|Relay (1.6)|FSM (1.2)|
|Watchdog (1.7)|Loop principal completo|
|Esquema tópicos (2.2)|Debe definirse antes de 1.5 y 3.3|
|Database (3.2)|Ninguna|
|Composite (3.1)|Ninguna|
|MQTTEventBus (3.3)|Mosquitto funcionando (2.1)|
|DecisionEngine (3.4)|MQTTEventBus (3.3), Database (3.2), Composite (3.1)|
|MainWindow (3.6)|MQTTEventBus (3.3), Composite (3.1), Database (3.2)|
|Memento (3.5)|Composite (3.1), Database (3.2)|
|Arranque auto base (3.7)|Todo lo anterior completo|