# FoT — Plan de Programación por Capas (v2 — corregido)

> Documento de referencia para la implementación del sistema Farm of Things.
> Cada tarea está descrita al nivel de lo que debe existir en el código, no solo lo que hace.
>
> **Cambios respecto a v1:** seis correcciones incorporadas tras revisión técnica.
> Ver [[#Registro de correcciones]] al final del documento.

---

## Índice

- [[#Capa 1 — Nodo de Campo (Arduino UNO R3, C++)]]
  - [[#1.0 Hardware de conectividad de red ★ nuevo]]
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
  - [[#3.4 Receptor de datos y persistencia (Observer)]]
  - [[#3.5 Snapshot de configuración (Memento)]]
  - [[#3.6 Interfaz gráfica (Tkinter)]]
  - [[#3.7 Arranque automático de la aplicación]]
- [[#Orden de implementación recomendado]]
- [[#Dependencias entre tareas]]
- [[#Registro de correcciones]]

---

## Capa 1 — Nodo de Campo (Arduino UNO R3, C++)

**Lenguaje:** C++
**Entorno:** Arduino IDE 2.x o PlatformIO
**Hardware objetivo:** Arduino UNO R3 + módulo RC522 + DHT22 + sensor capacitivo de humedad de suelo + relay + módulo de red (ver 1.0)
**Bibliotecas necesarias:**
- `DHT sensor library` (Adafruit) — lectura del DHT22
- `MFRC522` — comunicación SPI con el módulo RC522
- `PubSubClient` — cliente MQTT sobre TCP
- `WiFiEsp` o `Ethernet` — según módulo de red elegido (ver 1.0)
- `SoftwareSerial` — solo si se usa ESP-01 (ver 1.0)
- `EEPROM.h` — incluida en el núcleo de Arduino
- `avr/wdt.h` — watchdog timer del ATmega328P

---

### 1.0 Hardware de conectividad de red ★ nuevo

> El Arduino UNO R3 no tiene WiFi ni Ethernet integrados. Este apartado define el módulo de red, su conexión física y la biblioteca que usa `PubSubClient` como transporte. Es la decisión que desbloquea toda la sección 1.5.

#### Opción A — Shield Ethernet W5100 (recomendada para el prototipo)

**Por qué es la opción recomendada:** se conecta directamente como shield encima del UNO sin cables adicionales, sin conversión de niveles lógicos y sin configuración de AT commands. La biblioteca `Ethernet.h` es parte del núcleo oficial de Arduino. Es la opción más robusta para un prototipo de validación.

**Conexión física:** el shield se apila sobre el UNO. Ocupa los pines SPI (10, 11, 12, 13) igual que el RC522. Esto es un conflicto que debe resolverse: el RC522 y el W5100 comparten el bus SPI pero tienen pines SS distintos. El shield W5100 usa SS en el pin 10 por defecto; el RC522 puede moverse al pin 8 o 9. Ambos pueden coexistir en el bus SPI siempre que se active uno a la vez mediante sus pines SS respectivos.

**Configuración de pines con W5100 + RC522 en el mismo bus SPI:**
```
W5100  SS → pin 10  (fijo en el shield)
RC522  SS → pin 8   (mover de su default 10 al pin 8)
RC522 RST → pin 9
Ambos comparten SCK(13), MOSI(11), MISO(12)
```

**Biblioteca e instancia del cliente:**
```cpp
#include <Ethernet.h>
#include <PubSubClient.h>

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0x01 };
EthernetClient ethClient;
// Se pasa ethClient al constructor de MQTTClient (ver 1.5)
```

**Inicialización en setup():**
```cpp
Ethernet.begin(mac);  // DHCP automático
delay(1500);          // espera para que el shield establezca conexión
```

---

#### Opción B — Módulo ESP-01 por UART (si se necesita WiFi inalámbrico)

**Cuándo usar esta opción:** cuando el nodo de campo debe estar a distancia del router y no es posible tender cable Ethernet. Es la opción más cercana al escenario real de campo.

**Advertencia de recursos:** el ESP-01 por SoftwareSerial consume ciclos de CPU en la recepción de bytes. Con el ATmega328P a 16 MHz, puede generar interferencias con la temporización del DHT22 si se lee el sensor mientras hay tráfico UART. Solución: leer el DHT22 solo cuando el bus UART está en silencio.

**Conexión física del ESP-01:**
```
ESP-01 VCC  → 3.3V (¡NO 5V — el ESP-01 es de 3.3V!)
ESP-01 GND  → GND
ESP-01 TX   → pin 3 del UNO (RX de SoftwareSerial)
ESP-01 RX   → pin 2 del UNO (TX de SoftwareSerial) — VÍA DIVISOR DE TENSIÓN
              R1=1kΩ en serie, R2=2kΩ a GND: reduce 5V a ~3.3V en el RX del ESP-01
ESP-01 CH_PD → 3.3V (habilitar el módulo)
ESP-01 RST  → 3.3V (o a un pin digital para reset por software)
```

**Biblioteca e instancia:**
```cpp
#include <SoftwareSerial.h>
#include <WiFiEsp.h>
#include <PubSubClient.h>

SoftwareSerial espSerial(3, 2);   // RX=3, TX=2
WiFiEspClient wifiClient;
// Se pasa wifiClient al constructor de MQTTClient (ver 1.5)
```

**Inicialización en setup():**
```cpp
espSerial.begin(9600);
WiFiEsp.init(&espSerial);
WiFiEsp.begin("SSID_red_finca", "clave_wifi");
```

---

#### Decisión para la tesis

Para el prototipo de validación del Capítulo 3, usar la **Opción A (W5100)**. Documenta en el texto de la tesis que la opción WiFi (Opción B con ESP-01) está prevista para el despliegue en campo real y es arquitectónicamente equivalente porque `PubSubClient` recibe `Client&` y no depende de la implementación concreta del transporte. Esto demuestra que el diseño cumple RES-08 (múltiples medios físicos) sin necesidad de implementar todas las variantes.

---

### 1.1 Abstracción de sensores

**Patrón:** Adapter + Abstract Factory
**Archivos a crear:** `ISensor.h`, `SensorType.h`, `DHT22Adapter.h/.cpp`, `SoilMoistureAdapter.h/.cpp`, `SensorFactory.h/.cpp`

**Qué debe existir exactamente:**

#### `SensorType.h` ★ nuevo

Define el enum que reemplaza el uso de `String` para identificar tipos de sensor. Un `enum` ocupa 1 byte (`uint8_t`) y vive en flash, no en el heap.

```cpp
enum SensorType : uint8_t {
  SENSOR_DHT22_TEMP = 0,
  SENSOR_DHT22_HUM  = 1,
  SENSOR_SOIL_CAP   = 2
};
```

#### `ISensor.h`

Clase abstracta (interfaz pura). **Ningún método retorna `String`** — todos los identificadores son `const char*` apuntando a literales en memoria de programa (flash), usando la macro `F()` internamente en las implementaciones.

Métodos virtuales puros:
- `float read()` — lectura principal en unidad natural (°C o %).
- `bool isValid()` — `true` si la última lectura está dentro del rango operativo del sensor. Para el DHT22: temperatura entre -40 y 80 °C, humedad entre 0 y 100 %. Para el capacitivo: valor ADC entre 200 y 800 (los extremos 0 y 1023 indican cable desconectado).
- `SensorType getType()` — retorna el valor del enum, no una cadena.
- `const char* getUnitPGM()` — retorna un puntero a cadena en PROGMEM. Las implementaciones declaran internamente `static const char unit[] PROGMEM = "%";` y retornan ese puntero. El llamador usa `strcpy_P(buffer, sensor->getUnitPGM())` para copiar a RAM solo cuando necesita serializar.
- Destructor virtual vacío.

**Por qué no `String`:** cada objeto `String` en el ATmega328P realiza una asignación dinámica en el heap. Con 2 KB de SRAM total y varios objetos sensor activos, la fragmentación del heap puede provocar bloqueos que son imposibles de depurar en campo. Los `enum` y los punteros a PROGMEM no tocan el heap.

#### `DHT22Adapter.h/.cpp`

- Hereda de `ISensor`.
- Constructor: `DHT22Adapter(uint8_t pin, SensorType readingType)`.
- Internamente instancia `DHT dht(pin, DHT22)`.
- `read()`: llama a `dht.readTemperature()` o `dht.readHumidity()` según `readingType`. Almacena el resultado en un atributo privado `float _lastValue` para que `isValid()` pueda consultarlo sin releer el sensor.
- `isValid()`: comprueba que `_lastValue` no sea `NaN` (usando `isnan()` de `<math.h>`) y esté en rango.
- `getType()`: retorna el `SensorType` pasado al constructor.
- `getUnitPGM()`: retorna puntero a `"°C"` o `"%"` según tipo, ambos declarados `PROGMEM`.
- Llama a `mfrc522.PICC_HaltA()` al terminar cada lectura RFID para evitar lecturas dobles — nota: esto pertenece al RC522, no al DHT22; se menciona aquí solo para referencia cruzada.

#### `SoilMoistureAdapter.h/.cpp`

- Hereda de `ISensor`.
- Constructor: `SoilMoistureAdapter(uint8_t analogPin, int dryValue, int wetValue)`. Los parámetros `dryValue` (valor ADC en seco, típicamente ~800) y `wetValue` (valor ADC saturado, típicamente ~300) permiten calibración por parcela sin tocar el código.
- `read()`: llama a `analogRead(analogPin)`, almacena el crudo en `_rawValue`, y retorna `map(_rawValue, dryValue, wetValue, 0, 100)` como `float`.
- `isValid()`: retorna `(_rawValue > 100 && _rawValue < 950)` — los valores extremos indican sensor desconectado o cortocircuito.
- `getType()`: retorna `SENSOR_SOIL_CAP`.

#### `SensorFactory.h/.cpp`

- Método estático: `static ISensor* create(SensorType type, uint8_t pin, int param1 = 0, int param2 = 1023)`.
- El parámetro `type` es el enum, no una cadena — elimina la búsqueda de subcadenas en RAM.
- `param1` y `param2` se usan como `dryValue` y `wetValue` cuando `type == SENSOR_SOIL_CAP`.
- Si el tipo no es reconocido, retorna `nullptr`.

---

### 1.2 Máquina de estados (FSM)

**Patrón:** State  
**Archivos a crear:** `IState.h`, `StateIdle.h/.cpp`, `StateMonitoring.h/.cpp`, `StateIrrigating.h/.cpp`, `StateFault.h/.cpp`, `StateMachine.h/.cpp`



#### Principio de diseño central — el modo ES el estado

No existe una variable `operationMode` separada en ningún lugar del código. El modo de operación queda codificado en el estado activo de la FSM. La tabla siguiente define con precisión qué significa estar en cada estado:

|Estado|Quién decide|Lee sensores|Controla relay|Actúa autónomamente|
|---|---|:-:|:-:|:-:|
|`StateIdle`|El Farmer (vía UI)|✓|✓ bajo orden|✗|
|`StateMonitoring`|El Arduino solo|✓|✓ si umbral cruzado|✓|
|`StateIrrigating`|Nadie (es un efecto)|✓|✓ encendido|—|
|`StateFault`|Nadie|✗|✗ forzado apagado|✗|

**La diferencia clave entre `StateIdle` y `StateMonitoring` no es que uno lea sensores y el otro no. Es que uno actúa solo y el otro espera órdenes.** Ambos leen sensores y publican lecturas. Solo `StateMonitoring` evalúa los umbrales y decide regar sin intervención humana.

La transición `Idle → Monitoring` es el acto de activar el modo automático.  
La transición `Monitoring → Idle` es el acto de desactivarlo.  
Esto elimina cualquier condición adicional dentro de los estados — si estás en `StateMonitoring`, ya eres automático.



#### `IState.h`

Clase abstracta con un único método virtual puro:

```cpp
class StateMachine; // forward declaration

class IState {
public:
    virtual void handle(StateMachine& ctx) = 0;
    virtual ~IState() {}
};
```

El parámetro `ctx` es el contexto completo: acceso a sensores, umbrales, relay y cambio de estado. Los estados no tienen dependencias propias — todo llega a través de `ctx`.



#### `ISensor.h` — extensión requerida por la FSM

Para que `StateIdle` pueda habilitar y deshabilitar sensores individualmente, `ISensor` necesita dos métodos adicionales que no estaban en la versión base:

```cpp
// Añadir dentro de la clase abstracta ISensor:
protected:
    bool _enabled = true;

public:
    void setEnabled(bool v) { _enabled = v; }
    bool isEnabled() const  { return _enabled; }
```

El estado `_enabled` es volátil — vive en RAM y no se persiste en EEPROM. Tras un reinicio o un corte eléctrico, todos los sensores arrancan habilitados. Esto es el comportamiento correcto: el sistema no debe arrancar con sensores desconocidos apagados. Si el Farmer necesita desactivar un sensor de forma permanente, deberá hacerlo de nuevo desde la UI tras cada encendido.

Un sensor deshabilitado no produce lecturas y no puede causar una transición a `StateFault`. La FSM lo salta silenciosamente en cada ciclo.



#### `StateMachine.h/.cpp`

Contiene el estado actual como puntero a `IState` y todos los datos compartidos que los estados necesitan leer o modificar. Expone:

**Cambio de estado y ciclo principal:**

- `void setState(IState* newState)` — cambia el estado actual y libera el anterior con `delete`.
- `void tick()` — llama a `currentState->handle(*this)` una vez por iteración del `loop()` principal.

**Acceso a sensores:**

- `void updateSensors()` — itera la lista de sensores, llama a `read()` solo en los que tienen `isEnabled() == true`, y actualiza los valores internos. Llamado al inicio de `handle()` en los estados que leen sensores.
- `float getHumidity()` — última lectura del sensor capacitivo de suelo.
- `float getHumidityAir()` — última lectura de humedad del DHT22.
- `float getTemperature()` — última lectura de temperatura del DHT22.
- `void setSensorEnabled(SensorType type, bool enabled)` — itera la lista de sensores, busca el que coincide con `type` y llama a `sensor->setEnabled(enabled)`. Expuesto para que el callback MQTT lo pueda invocar desde fuera de los estados.

**Umbrales y configuración:**

- `float getThresholdMin()` — umbral mínimo de humedad desde el `ConfigData` en RAM.
- `float getThresholdMax()` — umbral de saturación desde el `ConfigData` en RAM.
- `void updateThresholds(float min, float max)` — actualiza los valores en RAM y persiste en EEPROM mediante `EEPROMConfig::save()`. Invocado cuando llega el comando `set_thresholds`.

**Relay:**

- `void setRelay(bool on)` — `digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF)`.

**Autenticación:**

- `bool isFarmerAuthenticated()` — `true` si el RFID fue validado en la sesión actual.
- `void setFarmerAuthenticated(bool v)` — llamado por `RFIDAuth` tras una lectura exitosa.

**Arranque tras corte eléctrico:**

- `void applyStartupState()` — lee `startInAutoMode` del `ConfigData` cargado desde EEPROM y llama a `setState(new StateMonitoring())` o `setState(new StateIdle())` en consecuencia. Llamado al final de `setup()`.

**Lo que `StateMachine` NO expone:** No hay `getOperationMode()` porque el modo está en el estado activo, no en una variable. No hay `setOperationMode()` porque cambiar de modo significa cambiar de estado — el comando MQTT `set_mode_auto` hace que el estado actual llame a `ctx.setState(new StateMonitoring())`.



#### `StateIdle` — control manual completo

Estado inicial y de control humano total. El Farmer puede ver los datos de los sensores, activar y detener la bomba manualmente, y habilitar o deshabilitar sensores individuales. El Arduino no toma ninguna decisión de riego por sí solo mientras está en este estado.

`handle(ctx)`:

**1. Lectura de sensores:** Llama a `ctx.updateSensors()` en cada intervalo periódico (igual que `StateMonitoring`). Los sensores deshabilitados se saltan. Las lecturas se publican por MQTT en `fot/<parcela>/sensores` para que el Farmer las vea en tiempo real en la UI y pueda decidir cuándo regar.

**2. Validación de sensores habilitados:** Si un sensor habilitado reporta `isValid() == false` tres lecturas consecutivas, transita a `StateFault`. Un sensor deshabilitado no puede provocar esta transición. El contador de lecturas inválidas se reinicia cuando llega una lectura válida.

**3. El relay no se fuerza a ningún estado al entrar:** A diferencia de `StateMonitoring` y `StateFault`, `StateIdle` no llama a `ctx.setRelay(false)` automáticamente al procesar cada tick. El relay conserva el estado que tenía. Esto es correcto: si el Farmer ordenó encender la bomba y la FSM está en `StateIdle`, la bomba debe seguir encendida hasta que llegue la orden `stop`. El relay solo cambia de estado cuando llega un comando explícito.

**4. Comandos MQTT aceptados en `StateIdle`:**

|Comando|Acción|
|---|---|
|`irrigate`|`ctx.setRelay(true)` → transita a `StateIrrigating` con `_cameFromAuto = false`|
|`stop`|`ctx.setRelay(false)` → permanece en `StateIdle`|
|`set_mode_auto`|Transita a `StateMonitoring`. Guarda `startInAutoMode=1` en EEPROM|
|`set_thresholds`|`ctx.updateThresholds(min, max)` → permanece en `StateIdle`|
|`enable_sensor`|`ctx.setSensorEnabled(type, true)` → permanece en `StateIdle`|
|`disable_sensor`|`ctx.setSensorEnabled(type, false)` → permanece en `StateIdle`|
|`reset_fault`|No aplica en `StateIdle` — ignorado|

**Comandos que `StateIdle` NO acepta:**

- `irrigate` no provoca riego automático repetido — solo una activación que lleva a `StateIrrigating`. El Farmer decide cuándo parar.
- `disable_sensor` sobre un sensor que ya reporta lecturas inválidas no limpia el contador de fallos. Si hay tres fallos acumulados, la transición a `StateFault` ya está en proceso.



#### `StateMonitoring` — modo automático

El sistema lee sensores, evalúa umbrales y decide regar sin intervención del Farmer. Es el único estado con agencia propia.

`handle(ctx)`:

**1.** Llama a `ctx.setRelay(false)` como primera acción del tick — garantiza que el relay está apagado mientras el sistema evalúa si debe regar. Esto previene que el relay quede encendido por una transición inesperada desde `StateIrrigating`.

**2.** Llama a `ctx.updateSensors()`.

**3.** Acumula lecturas inválidas de sensores habilitados. Si `invalidCount >= 3`, transita a `StateFault`.

**4.** Si las lecturas son válidas y `ctx.getHumidity() < ctx.getThresholdMin()`: transita a `StateIrrigating` con `_cameFromAuto = true`. No hay condición adicional de modo — estar en `StateMonitoring` ya es el modo automático.

**5.** Publica lecturas por MQTT en `fot/<parcela>/sensores`.

**6.** Comandos MQTT aceptados:

|Comando|Acción|
|---|---|
|`set_mode_manual`|Transita a `StateIdle`. Guarda `startInAutoMode=0` en EEPROM|
|`set_thresholds`|`ctx.updateThresholds(min, max)` → permanece en `StateMonitoring`|
|`enable_sensor`|`ctx.setSensorEnabled(type, true)` → permanece en `StateMonitoring`|
|`disable_sensor`|`ctx.setSensorEnabled(type, false)` → permanece en `StateMonitoring`. **Nota:** deshabilitar el sensor de humedad de suelo en modo automático impide que el sistema detecte cuándo regar. Es decisión del Farmer — el Arduino no lo bloquea|
|`irrigate`|**Ignorado** — en modo automático el Arduino decide cuándo regar, no la UI|
|`stop`|**Ignorado** — si el sistema está en `StateMonitoring` no hay riego activo que detener. Si está regando está en `StateIrrigating`, no aquí|



#### `StateIrrigating` — bomba activa

El relay está encendido. Este estado es un efecto de una decisión tomada en otro estado, no un modo de operación en sí mismo. Puede ser alcanzado desde `StateMonitoring` (decisión automática) o desde `StateIdle` (orden manual del Farmer).

`handle(ctx)`:

**1.** Llama a `ctx.setRelay(true)` como primera acción.

**2.** En la primera ejecución del estado, registra el tiempo de inicio: `_startTime = millis()`.

**3.** Lee humedad periódicamente con `ctx.updateSensors()`.

**4.** Condiciones de salida:

|Condición|Acción|
|---|---|
|`ctx.getHumidity() >= ctx.getThresholdMax()`|`setRelay(false)` → regresa a estado de origen (`StateMonitoring` si `_cameFromAuto`, `StateIdle` si no)|
|`millis() - _startTime >= ctx.getIrrigationTimeout() * 1000UL`|`setRelay(false)` → transita a `StateFault` (timeout de seguridad)|
|Llega comando `stop`|`setRelay(false)` → regresa a estado de origen|
|Sensor habilitado inválido 3 veces seguidas|`setRelay(false)` → transita a `StateFault`|

**5.** El flag `_cameFromAuto` se establece en el constructor del estado y no cambia durante su ejecución. Determina a qué estado regresar al salir.

**Nota importante:** cuando el Farmer envía `stop` desde `StateIrrigating` y el origen era `StateIdle`, el sistema vuelve a `StateIdle` con el relay apagado. El Farmer puede volver a ordenar `irrigate` inmediatamente si lo necesita.



#### `StateFault` — fallo de sensor o timeout

El relay está apagado de forma forzosa e irrevocable hasta que el Farmer intervenga explícitamente. El sistema no intenta recuperarse por sí solo.

`handle(ctx)`:

**1.** Llama a `ctx.setRelay(false)` como primera acción — garantía absoluta de que la bomba está apagada.

**2.** Publica el tipo de fallo por MQTT en `fot/<parcela>/estado`. Tipos posibles: `"sensor_invalid"` (lecturas fuera de rango), `"irrigation_timeout"` (timeout de seguridad superado).

**3.** Solo acepta dos eventos externos:

|Evento|Acción|
|---|---|
|Comando MQTT `reset_fault`|Transita a `StateIdle`. El relay permanece apagado al entrar en `Idle` hasta que el Farmer ordene otra cosa|
|Reset físico por watchdog|El microcontrolador se reinicia. `setup()` carga la EEPROM. Si `startInAutoMode=1`, el sistema intenta volver a `StateMonitoring`. Si el sensor sigue fallando, volverá a `StateFault` en el primer ciclo|

**4.** Cualquier otro comando MQTT (incluidos `irrigate`, `enable_sensor`, `set_mode_auto`) es **ignorado** mientras el sistema está en `StateFault`. El Farmer debe resolver el problema físico (reconectar el sensor, verificar el cableado) y luego enviar `reset_fault` desde la UI.



#### Diagrama de transiciones

```
                    ┌─────────────────────────────────────────────┐
                    │               ARRANQUE                       │
                    │  EEPROMConfig::load() → applyStartupState()  │
                    └──────────┬──────────────────┬───────────────┘
                               │ startInAutoMode=0 │ startInAutoMode=1
                               ▼                   ▼
                        ┌────────────┐      ┌──────────────────┐
           ┌────────────│  StateIdle  │◄─────│ StateMonitoring  │
           │   stop     │  (manual)   │      │  (automático)    │──────────┐
           │            └─────┬──────┘      └────────┬─────────┘          │
           │                  │ irrigate              │ hum<min             │
           │    set_mode_auto ├──────────────────────►│                    │ sensor
           │    ◄─────────────┘                       │                    │ inválido
           │    set_mode_manual ◄────────────────────┐│                    │ ×3
           │                                         ││                    │
           │                               ┌─────────▼▼────────┐          │
           └────────────────────────────── │  StateIrrigating  │          │
                                           │  (bomba activa)   │          │
                                           └─────────┬─────────┘          │
                                 timeout o           │ hum>=max            │
                                 sensor inválido ×3  │ o stop              │
                                           │         └───► estado origen   │
                                           │                               │
                                           ▼                               │
                                    ┌─────────────┐◄──────────────────────┘
                                    │  StateFault  │
                                    │  (fallo)     │
                                    └──────┬───────┘
                                           │ reset_fault
                                           ▼
                                      StateIdle
```



#### Despacho de comandos MQTT en la FSM

El callback `onMessage` en `MQTTClient` no llama directamente a los métodos de los estados — los estados no son accesibles desde fuera de la `StateMachine`. En su lugar, `StateMachine` expone un método de despacho que el callback invoca:

```cpp
void StateMachine::dispatchCommand(const char* cmd, const char* param1, float val1, float val2) {
    // Comandos que la StateMachine maneja directamente (no dependen del estado):
    if (strncmp(cmd, "enable_sensor",  13) == 0) { setSensorEnabled(sensorTypeFromStr(param1), true);  return; }
    if (strncmp(cmd, "disable_sensor", 14) == 0) { setSensorEnabled(sensorTypeFromStr(param1), false); return; }
    if (strncmp(cmd, "set_thresholds", 14) == 0) { updateThresholds(val1, val2);                        return; }

    // Comandos que se delegan al estado actual:
    _pendingCmd = cmd;    // el estado actual lo leerá en su próxima llamada a handle()
}
```

El atributo `_pendingCmd` es un `const char*` en RAM que el estado actual consulta al inicio de su `handle()` y limpia después de procesarlo. Este mecanismo evita que el callback llame a `setState()` directamente desde el hilo de red, lo que podría corromper la FSM si `tick()` está ejecutándose al mismo tiempo.



#### Función auxiliar `sensorTypeFromStr`

Necesaria para el despacho de `enable_sensor` y `disable_sensor`. Vive en `StateMachine.cpp`:

```cpp
SensorType sensorTypeFromStr(const char* name) {
    if (strncmp(name, "DHT22_TEMP", 10) == 0) return SENSOR_DHT22_TEMP;
    if (strncmp(name, "DHT22_HUM",   9) == 0) return SENSOR_DHT22_HUM;
    if (strncmp(name, "SOIL_CAP",    8) == 0) return SENSOR_SOIL_CAP;
    return (SensorType)255;  // tipo no reconocido — ignorar el comando
}
```

No usa `String`, no hace allocaciones. Compara con `strncmp` sobre el buffer de stack del callback.






- - -
### 1.3 Persistencia en EEPROM (Memento)

**Patrón:** Memento
**Archivo a crear:** `EEPROMConfig.h/.cpp`

**Qué debe existir exactamente:**

#### `struct ConfigData`

```cpp
struct ConfigData {
  float    humidityThresholdMin;   // % — umbral para activar riego
  float    humidityThresholdMax;   // % — umbral de saturación
  uint16_t irrigationTimeoutSec;   // segundos máximos de riego continuo
  uint16_t monitoringIntervalSec;  // segundos entre lecturas en auto
  uint8_t  rfidUID[4];             // UID de la tarjeta autorizada
  // NOTA: no hay campo operationMode — el modo lo codifica la FSM en EEPROM
  //       solo como dato de arranque: 0 = arrancar en Idle, 1 = en Monitoring
  uint8_t  startInAutoMode;        // 0 = Idle al arrancar, 1 = Monitoring al arrancar
  uint8_t  checksum;               // XOR de todos los bytes anteriores
};
```

El campo `startInAutoMode` resuelve el arranque tras corte eléctrico: si antes del corte el sistema estaba en modo automático, debe reanudarlo. Se escribe en EEPROM cada vez que la FSM transita entre `StateIdle` y `StateMonitoring`.

#### `EEPROMConfig.h/.cpp`

- `void save(const ConfigData& cfg)` — serializa el struct byte a byte en EEPROM desde dirección 0. Calcula el checksum como XOR de todos los bytes del struct excepto el propio checksum, y lo escribe al final. Usa `EEPROM.update()` en lugar de `EEPROM.write()` para no gastar ciclos de escritura si el valor no cambió (la EEPROM del ATmega soporta ~100 000 ciclos por celda).
- `bool load(ConfigData& cfg)` — lee el struct, recalcula el checksum y compara. Si no coincide, llama a `writeDefaults(cfg)` y retorna `false`.
- `void writeDefaults(ConfigData& cfg)` — valores seguros: `humMin=30.0`, `humMax=70.0`, `timeout=300`, `interval=60`, `uid={0,0,0,0}`, `startInAutoMode=0`.

**Por qué `EEPROM.update()` en lugar de `write()`:** `write()` escribe siempre aunque el valor sea igual. `update()` lee primero y solo escribe si el dato cambió. Dado que los umbrales se actualizan frecuentemente, esto puede multiplicar por 10 la vida útil de la EEPROM en uso continuo.

---

### 1.4 Autenticación RFID (RC522)

**Patrón:** ninguno GoF específico; usa EEPROM para persistencia
**Biblioteca:** `MFRC522`
**Archivo a crear:** `RFIDAuth.h/.cpp`

**Qué debe existir exactamente:**

#### Conexión hardware del RC522 con el UNO R3 — niveles lógicos

> ⚠️ ADVERTENCIA DE HARDWARE: El RC522 opera a 3.3 V. Sus pines SPI (SCK, MOSI, SS) **no son tolerantes a señales de 5 V**. El Arduino UNO genera señales de 5 V en todos sus pines digitales. Conectar directamente puede funcionar a corto plazo pero degrada el módulo y puede dañarlo.

**Solución requerida:** un conversor de nivel lógico bidireccional de 4 canales (tipo TXS0108E, o el módulo de 4 canales de bajo costo basado en BSS138 que se encuentra ampliamente en el mercado). Se conecta entre los pines SPI del UNO y los pines correspondientes del RC522.

**Alternativa práctica:** verificar si el breakout del RC522 que tienes ya incluye el conversor. Muchos módulos RC522 del mercado chino incluyen un regulador AMS1117-3.3 y resistencias de pull-up, pero no necesariamente el conversor de señal. Revisar el esquemático del módulo o medir con multímetro los niveles de señal antes de conectar.

**Pines con W5100 en el bus SPI (ajustados respecto a la conexión original):**
```
RC522 SDA (SS) → pin 8  (movido del default 10, que lo usa el W5100)
RC522 SCK      → pin 13 (bus SPI compartido, VÍA CONVERSOR)
RC522 MOSI     → pin 11 (bus SPI compartido, VÍA CONVERSOR)
RC522 MISO     → pin 12 (bus SPI compartido, VÍA CONVERSOR)
RC522 RST      → pin 9
RC522 VCC      → 3.3V
RC522 GND      → GND
```

Estas conexiones deben estar documentadas en comentario al inicio del `.ino` junto con el diagrama de pines.

#### `RFIDAuth.h/.cpp`

- Constructor: `RFIDAuth(uint8_t ssPin, uint8_t rstPin)`.
- `void begin()` — inicializa `SPI.begin()` y llama a `mfrc522.PCD_Init()`.
- `bool isCardPresent()` — retorna `mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()`.
- `bool authenticate(const uint8_t* storedUID)` — compara los 4 bytes del `mfrc522.uid.uidByte` con `storedUID` usando `memcmp`. Llama a `mfrc522.PICC_HaltA()` al terminar para prevenir lecturas dobles en el siguiente tick.
- `void getUID(uint8_t* buffer)` — copia `mfrc522.uid.uidByte[0..3]` al buffer.
- `void enrollNewCard(ConfigData& cfg)` — lee el UID presente y lo copia en `cfg.rfidUID`. Llama a `EEPROMConfig::save(cfg)`. Solo invocable desde `StateIdle` con autenticación previa de administrador (puede ser una tarjeta maestra con UID fijo en flash).

---

### 1.5 Cliente MQTT (PubSubClient)

**Biblioteca:** `PubSubClient`
**Depende de:** sección 1.0 (módulo de red elegido)
**Archivo a crear:** `MQTTClient.h/.cpp`

**Qué debe existir exactamente:**

#### `MQTTClient.h/.cpp`

- Constructor: `MQTTClient(Client& networkClient, const char* brokerIP, uint16_t brokerPort, const char* parcelaId)`.
  - El tipo `Client&` es la interfaz abstracta de Arduino. `EthernetClient` y `WiFiEspClient` la implementan. El `MQTTClient` no sabe ni le importa cuál es — esto satisface la extensibilidad de RES-08.
- `void begin()` — `pubSubClient.setServer(brokerIP, brokerPort)` y `pubSubClient.setCallback(onMessage)`. Configura el buffer de mensajes: `pubSubClient.setBufferSize(256)` (suficiente para el payload JSON de sensores).
- `bool connect()`:
  ```
  para cada intento (máximo 3):
      wdt_reset()                      ← ★ CORRECCIÓN: evitar disparo del watchdog
      intentar pubSubClient.connect(clientId)
      si éxito:
          suscribirse a fot/<parcelaId>/control con QoS 1
          retornar true
      esperar 1000 ms                  ← ★ CORRECCIÓN: reducido de 2000ms a 1000ms
  retornar false
  ```
  El `wdt_reset()` al inicio de cada intento garantiza que el watchdog no dispare durante la fase de reconexión, que puede bloquear hasta 3 segundos en total (3 intentos × 1 s de espera, más los timeouts de red del propio socket).
- `void loop()` — llama a `pubSubClient.loop()`. Si `!pubSubClient.connected()`, llama a `connect()`.
- `void publishSensorData(float humSuelo, float humAire, float temp, uint32_t uptime)` — construye JSON con `snprintf` en un buffer `char[128]` en stack (no heap):
  ```cpp
  char buf[128];
  snprintf(buf, sizeof(buf),
    "{\"hum_suelo\":%.1f,\"hum_aire\":%.1f,\"temp\":%.1f,\"ts\":%lu}",
    humSuelo, humAire, temp, uptime);
  pubSubClient.publish(topic, buf, false);
  ```
- `void publishState(const char* stateName, bool relayOn, uint32_t uptime)` — mismo patrón con `snprintf`.
- Función callback `onMessage(char* topic, byte* payload, unsigned int length)`:
  - Copia el payload a un buffer terminado en `\0`: `char msg[64]; memcpy(msg, payload, min(length, 63)); msg[min(length,63)] = '\0';`
  - Busca el valor de `"cmd"` con `strstr`. Compara el resultado con cadenas literales conocidas usando `strcmp` o `strncmp`, no con `String`. Esto evita heap dinámico.
  - Llama al dispatcher de la FSM según el comando reconocido.

**Nota sobre el parseo con `strstr`:** para el conjunto fijo de comandos del sistema (`irrigate`, `stop`, `reset_fault`, `set_mode_auto`, `set_mode_manual`, `set_thresholds`), `strstr` es suficiente y predecible. Si el payload está malformado, en el peor caso no se reconoce ningún comando — el sistema no actúa. El riesgo de falso positivo es bajo porque los nombres de comando son suficientemente únicos.

**Tópicos:**
- Publica en: `fot/<parcelaId>/sensores`, `fot/<parcelaId>/estado`
- Suscrito a: `fot/<parcelaId>/control`

---

### 1.6 Control del relay

**No requiere clase propia — lógica en `StateMachine.cpp` y los estados**

**Qué debe existir exactamente:**

- Constante `RELAY_PIN` definida en el `.ino` principal (p.ej. pin 7).
- El relay de módulos de 1 canal comunes es activo en bajo:
  ```cpp
  #define RELAY_ON  LOW   // escribir LOW activa la bobina
  #define RELAY_OFF HIGH  // escribir HIGH desactiva
  ```
  Documentado con comentario para que sea obvio al revisar el código.
- `StateMachine::setRelay(bool on)` → `digitalWrite(RELAY_PIN, on ? RELAY_ON : RELAY_OFF)`.
- **Regla de seguridad:** `ctx.setRelay(false)` es la **primera línea** de `handle()` en `StateIdle`, `StateMonitoring` y `StateFault`. Solo `StateIrrigating` puede llamar a `setRelay(true)`. Si la FSM transita inesperadamente a cualquier otro estado, el relay se apaga en la siguiente llamada a `tick()`.

---

### 1.7 Watchdog timer

**Archivo:** `main.ino`

**Qué debe existir exactamente:**

- `wdt_enable(WDTO_8S)` al **final** de `setup()`, después de inicializar todos los componentes. Si se activa al inicio y la inicialización de la red tarda más de 8 s, el sistema entraría en un bucle de reset.
- `wdt_reset()` al final de cada iteración del `loop()` principal.
- `wdt_reset()` también al inicio de cada intento de reconexión en `MQTTClient::connect()` (ver 1.5).
- Si el `loop()` se bloquea más de 8 s, el microcontrolador se reinicia. `setup()` carga `ConfigData` desde EEPROM y lee `startInAutoMode` para decidir si arranca en `StateIdle` o `StateMonitoring`.
- **Todo el código de temporización usa `millis()`**, no `delay()`. Un `delay()` de más de 8 s sin `wdt_reset()` dispararía el watchdog. Usar el patrón:
  ```cpp
  if (millis() - lastActionTime >= intervalMs) {
      lastActionTime = millis();
      // acción periódica
  }
  ```

---

## Capa 2 — Comunicación (Eclipse Mosquitto)

**No se escribe código propio en esta capa.** Se configura un servicio existente.
**Sistema operativo objetivo:** Linux (primario) y Windows (secundario)

---

### 2.1 Instalación y archivo de configuración

**Archivo a editar:** `/etc/mosquitto/mosquitto.conf` (Linux) o `C:\mosquitto\mosquitto.conf` (Windows)

```
listener 1883
allow_anonymous true
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
```

**Por qué `allow_anonymous true` es aceptable:** el broker escucha solo en la red local (RES-09). En despliegue final puede añadirse `password_file` para autenticación básica.

**Verificación:**
```bash
# Terminal 1:
mosquitto_sub -h localhost -t "fot/#" -v

# Terminal 2:
mosquitto_pub -h localhost -t "fot/p1/sensores" -m '{"hum_suelo":42.5,"hum_aire":65.0,"temp":28.3,"ts":0}'
```
Si el mensaje aparece en el terminal 1, el broker funciona.

---

### 2.2 Esquema de tópicos y formato de mensajes

#### Tópicos definidos

| Tópico | Publicado por | Suscrito por |
|--------|---------------|--------------|
| `fot/<parcela>/sensores` | Arduino | Estación base |
| `fot/<parcela>/estado` | Arduino | Estación base |
| `fot/<parcela>/control` | Estación base (solo manual) | Arduino |

`<parcela>`: identificador corto sin espacios (`p1`, `norte`, `sur`).

#### Payloads JSON

**`fot/<parcela>/sensores`**
```json
{ "hum_suelo": 42.5, "hum_aire": 65.0, "temp": 28.3, "ts": 3600 }
```
`ts`: segundos de uptime del Arduino (no es Unix time — el UNO no tiene RTC). La estación base aplica el timestamp real al recibir.

**`fot/<parcela>/estado`**
```json
{ "state": "Monitoring", "relay": false, "uptime": 3600 }
```
`state`: `"Idle"` | `"Monitoring"` | `"Irrigating"` | `"Fault"`

**`fot/<parcela>/control`** (solo desde la UI manual del Farmer)
```json
{ "cmd": "irrigate" }
```
Comandos posibles: `irrigate`, `stop`, `reset_fault`, `set_mode_auto`, `set_mode_manual`, `set_thresholds` (con campos adicionales `min` y `max`).

**Comando para sincronizar umbrales:**
```json
{ "cmd": "set_thresholds", "min": 35.0, "max": 75.0 }
```
El Arduino al recibir este comando actualiza su `ConfigData` en RAM y llama a `EEPROMConfig::save()`.

---

### 2.3 Arranque automático del broker

**Linux:**
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto
```

**Windows — Tarea Programada:**
Ejecuta `C:\mosquitto\mosquitto.exe -c C:\mosquitto\mosquitto.conf` al inicio del sistema, bajo cuenta de sistema, sin sesión de usuario.

---

## Capa 3 — Estación Base (Python 3 + SQLite)

**Lenguaje:** Python 3.8+
**Bibliotecas:**
- `paho-mqtt` (pip)
- `sqlite3`, `tkinter`, `json`, `threading`, `datetime` (stdlib)

**Estructura de archivos:**
```
estacion_base/
├── main.py
├── domain/
│   ├── components.py     ← Composite
│   └── memento.py        ← Memento
├── data/
│   ├── database.py       ← DAO
│   └── fot.db            ← generado en runtime
├── mqtt/
│   └── mqtt_client.py    ← Subject (Observer)
├── logic/
│   └── data_receiver.py  ← Observer (solo persistencia, sin decisiones)
└── ui/
    └── main_window.py    ← Observer + control manual
```

---

### 3.1 Modelo de dominio (Composite)

**Patrón:** Composite
**Archivo:** `domain/components.py`

#### Clase abstracta `IComponente`
- `get_id() -> str`
- `get_name() -> str`
- `get_latest_reading() -> dict`
- `get_children() -> list`
- `apply(operation: callable)` — aplica recursivamente a todos los hijos.

#### Clase `Dispositivo` (hoja)
- Atributos: `id`, `name`, `parcela_id`, `tipo` (`"sensor"` o `"actuador"`), `last_reading: dict`.
- `get_children()` → `[]`
- `update_reading(data: dict)` — actualiza `last_reading`.

#### Clase `Parcela` (nodo intermedio)
- Atributos: `id`, `name`, `umbral_min: float`, `umbral_max: float`, `modo: str` (`"auto"` | `"manual"`), `dispositivos: list`.
- `add_device(d)`, `remove_device(device_id)`.
- `get_latest_reading()` — agrega lecturas de todos sus dispositivos.

**Nota sobre `modo` en `Parcela`:** este campo refleja el modo que la estación base conoce del nodo, recibido a través del tópico `/estado`. La fuente de verdad del modo es siempre el Arduino. La base no usa este campo para tomar decisiones de riego; lo usa solo para mostrar el estado en la UI y para saber si los botones manuales deben estar habilitados.

#### Clase `Finca` (raíz)
- Atributos: `id`, `name`, `parcelas: list`.
- `add_parcela(p)`, `remove_parcela(parcela_id)`.
- `get_parcela(parcela_id: str) -> Parcela`.
- `get_all_readings() -> list[dict]` — vía `apply()`.

---

### 3.2 Base de datos SQLite

**Patrón:** DAO
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

**Mantenimiento de la base de datos — rotación de lecturas:**
La tabla `lecturas` crecerá indefinidamente. Añadir este método a la clase `Database`:
- `def purge_old_readings(self, days: int = 30)` — ejecuta `DELETE FROM lecturas WHERE ts_base < datetime('now', '-30 days')`. Llamar desde `main.py` al arrancar la aplicación una vez al día.

**Clase `Database`:**
- Constructor: `sqlite3.connect(db_path, check_same_thread=False)`. El argumento es necesario porque el hilo MQTT y el hilo de UI acceden concurrentemente.
- Todos los métodos protegidos por `threading.Lock`.
- `initialize()` — crea tablas si no existen.
- `save_reading(parcela_id, data)`, `save_event(parcela_id, tipo, descripcion)`.
- `get_readings(parcela_id, limit=100) -> list[dict]` — últimas N lecturas en `DESC`.
- `get_parcelas() -> list[dict]`, `save_parcela(parcela: dict)` (UPSERT).
- `save_snapshot(descripcion, datos_json)`, `get_snapshots() -> list[dict]`.
- `purge_old_readings(days=30)`.

---

### 3.3 Motor de eventos MQTT (Observer)

**Patrón:** Observer (Subject)
**Archivo:** `mqtt/mqtt_client.py`

#### Clase `MQTTEventBus` (Subject)

- `_observers: list` — objetos con método `on_event(topic: str, data: dict)`.
- `register(observer)`, `unregister(observer)`.
- `_notify(topic, data)` — itera observers, captura excepciones individuales sin detener la cadena.
- `start()` — crea `paho.mqtt.client.Client`, registra `on_connect` y `on_message`, llama a `client.connect()` y `client.loop_start()` (hilo de red en segundo plano).
- `stop()` — `client.loop_stop()` + `client.disconnect()`.
- `on_connect`: si `rc == 0`, suscribe a `fot/+/sensores` y `fot/+/estado` con QoS 1.
- `on_message`: `json.loads()` del payload, llama a `_notify()`. Captura `json.JSONDecodeError`.
- `publish(topic, payload: dict)` — `client.publish(topic, json.dumps(payload), qos=1)`.

---

### 3.4 Receptor de datos y persistencia (Observer)

> ★ CORRECCIÓN respecto a v1: esta clase ya no se llama `DecisionEngine` ni toma decisiones de riego automático. La única entidad que decide regar en modo automático es el Arduino. La estación base recibe datos, los persiste y notifica a la UI. El control manual lo ejerce la UI directamente a través de `MQTTEventBus.publish()`.

**Patrón:** Observer (Observer concreto)
**Archivo:** `logic/data_receiver.py`

#### Clase `DataReceiver`

- Implementa `on_event(topic: str, data: dict)`.
- Constructor: `DataReceiver(db: Database, finca: Finca)`. No recibe `mqtt_bus` porque no publica comandos.
- `on_event(topic, data)`:
  - Extrae `parcela_id = topic.split('/')[1]`.
  - Si el tópico termina en `/sensores`:
    1. `db.save_reading(parcela_id, data)`.
    2. Obtiene el `Dispositivo` correspondiente del modelo de dominio y llama a `update_reading(data)`.
  - Si el tópico termina en `/estado`:
    1. Actualiza el campo `modo` y el estado en el modelo de dominio.
    2. Si `data.get('state') == 'Fault'`: `db.save_event(parcela_id, 'fault', str(data))`.
  - No evalúa umbrales. No publica comandos. No tiene lógica de riego.

**Dónde vive la lógica de control manual:** en `MainWindow`. Cuando el Farmer pulsa "Activar riego", la UI llama a `mqtt_bus.publish(f'fot/{parcela_id}/control', {"cmd": "irrigate"})`. Cuando pulsa "Aplicar umbrales", la UI publica `{"cmd": "set_thresholds", "min": ..., "max": ...}`. La UI es el único origen de comandos de control desde la estación base.

---

### 3.5 Snapshot de configuración (Memento)

**Patrón:** Memento
**Archivo:** `domain/memento.py`

#### Clase `ConfigSnapshot`
- Atributos: `_state: str` (JSON de parcelas), `_timestamp: str`.
- `get_state() -> str`.

#### Clase `ConfigManager`
- `save_snapshot(finca, descripcion, db)` — serializa la jerarquía a JSON y persiste en `configuracion_snapshots`.
- `list_snapshots(db) -> list[dict]`.
- `restore_snapshot(snapshot_id, db) -> dict` — retorna dict para reconstruir la jerarquía.
- La UI llama a `save_snapshot()` automáticamente **antes** de cualquier edición de parcelas.

---

### 3.6 Interfaz gráfica (Tkinter)

**Patrón:** Observer (Observer concreto)
**Archivo:** `ui/main_window.py`

#### Clase `MainWindow`

- Implementa `on_event(topic, data)`.
- Constructor: `MainWindow(root, finca, mqtt_bus, db, config_manager)`.

#### Estructura de la ventana

**Panel lateral izquierdo — árbol de parcelas:**
- `ttk.Treeview` con jerarquía `Finca → Parcela → Dispositivo`.
- Botones: "Añadir parcela", "Eliminar parcela" (con confirmación que llama a `save_snapshot()` antes de proceder), "Guardar snapshot".

**Panel central — datos de la parcela seleccionada:**
- Lecturas actuales: `hum_suelo`, `hum_aire`, `temp` como `tk.Label` actualizados en tiempo real.
- Indicador de estado FSM con color: Monitoring = verde, Irrigating = azul, Fault = rojo, Idle = gris.
- Campos de umbral editables (`ttk.Entry`). Botón "Aplicar" que:
  1. Llama a `save_snapshot()`.
  2. Actualiza la `Parcela` en el modelo de dominio.
  3. Guarda en SQLite.
  4. Publica `{"cmd": "set_thresholds", "min": ..., "max": ...}` por MQTT para sincronizar el Arduino.
- Selector de modo (`ttk.Combobox` con valores "auto" y "manual"). Al cambiar, publica el comando correspondiente.
- Botones de control manual "Activar riego" y "Detener riego" — habilitados solo si el estado conocido es `Idle` (modo manual). Publican `{"cmd": "irrigate"}` y `{"cmd": "stop"}`.

**Panel inferior — log de eventos:**
- `tk.Text` en modo solo lectura. Los últimos N eventos de la base de datos, y los nuevos que lleguen en tiempo real.

#### Actualización segura desde el hilo MQTT
- `on_event()` se ejecuta en el hilo de red de paho-mqtt.
- Llamar directamente a métodos de Tkinter desde ese hilo corrompe el event loop.
- Solución: `self.root.after(0, self._update_ui, topic, data)`. El `after(0, ...)` encola la actualización en el hilo principal de Tkinter.
- `_update_ui(topic, data)` puede modificar widgets con seguridad.

---

### 3.7 Arranque automático de la aplicación

**Linux — `estacion_base.service`:**
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

`After=mosquitto.service` garantiza que el broker esté activo antes de que Python intente conectarse. `Restart=on-failure` relanza si el proceso termina con error.

---

## Orden de implementación recomendado

```
1. [C++]    SensorType.h + ISensor.h + DHT22Adapter + SoilMoistureAdapter + SensorFactory
              → Prueba: leer sensores en monitor serie, verificar que no hay String en el código.

2. [C++]    EEPROMConfig (load/save/defaults + checksum)
              → Prueba: guardar ConfigData, apagar, encender, verificar que los valores persisten.

3. [C++]    RFIDAuth (con conversor de nivel lógico conectado)
              → Prueba: imprimir UID en monitor serie al acercar tarjeta.

4. [Config] Instalar Mosquitto y verificar con mosquitto_sub / mosquitto_pub.

5. [C++]    FSM completa (StateIdle, StateMonitoring, StateIrrigating, StateFault)
              sin MQTT aún, con relay simulado en LED
              → Prueba: verificar transiciones de estado en monitor serie con entradas simuladas.

6. [Hardware] Conectar módulo de red (W5100 o ESP-01 según elección de 1.0)
              → Prueba: ping al broker desde el Arduino, sin MQTT aún.

7. [C++]    MQTTClient con wdt_reset() en reconexión
              → Prueba: publicar lecturas y verificar en mosquitto_sub.

8. [Python] Database (esquema + DAO + purge)
              → Prueba: insertar lecturas desde script de prueba, verificar con sqlite3 CLI.

9. [Python] IComponente + Finca + Parcela + Dispositivo
              → Prueba: construir jerarquía, llamar apply(), recorrer el árbol.

10. [Python] MQTTEventBus + DataReceiver
              → Prueba: con Arduino enviando datos, verificar que la DB recibe lecturas.

11. [Python] MainWindow Tkinter (primero visualización, luego botones de control)
              → Prueba: ver lecturas en tiempo real y enviar comando manual desde la UI.

12. [Python] ConfigManager (Memento)
              → Prueba: snapshot antes de editar, restaurar, verificar que los valores vuelven.

13. [Config] Arranque automático de Mosquitto y la aplicación Python.
```

---

## Dependencias entre tareas

| Tarea | Depende de |
|-------|-----------|
| FSM (1.2) | ISensor (1.1), SensorType (1.1) |
| EEPROM (1.3) | Ninguna |
| RFID (1.4) | EEPROM (1.3), conversor de nivel lógico instalado |
| Módulo de red (1.0) | Decisión hardware tomada |
| MQTTClient (1.5) | FSM (1.2), módulo de red (1.0) |
| Relay (1.6) | FSM (1.2) |
| Watchdog (1.7) | Loop principal completo, wdt_reset en 1.5 |
| Esquema tópicos (2.2) | Debe definirse antes de 1.5 y 3.3 |
| Database (3.2) | Ninguna |
| Composite (3.1) | Ninguna |
| MQTTEventBus (3.3) | Mosquitto funcionando (2.1) |
| DataReceiver (3.4) | MQTTEventBus (3.3), Database (3.2), Composite (3.1) |
| MainWindow (3.6) | MQTTEventBus (3.3), Composite (3.1), Database (3.2) |
| Memento (3.5) | Composite (3.1), Database (3.2) |
| Arranque auto (3.7) | Todo lo anterior |

---

## Registro de correcciones

Este documento corrige seis problemas detectados en la revisión técnica de v1.

**C1 — Módulo de red del Arduino (sección 1.0, nueva)**
v1 no especificaba qué hardware de red usar. Se añade la sección 1.0 con dos opciones documentadas (W5100 y ESP-01), criterios de elección y manejo del conflicto de pines SPI con el RC522.

**C2 — Conflicto de control dual (sección 3.4, reescrita)**
v1 tenía un `DecisionEngine` que duplicaba la lógica de riego del Arduino. El Arduino es el único cerebro en modo automático. La clase se renombra a `DataReceiver` y solo persiste datos y actualiza el modelo de dominio. La UI es el único origen de comandos desde la estación base.

**C3 — Modo codificado en el estado, no en variable (sección 1.2, revisada)**
v1 tenía una variable `operationMode` en `ConfigData` que los estados consultaban. Se elimina: estar en `StateMonitoring` ya implica modo automático. Estar en `StateIdle` implica manual. Se conserva solo `startInAutoMode` en EEPROM para el arranque tras corte eléctrico.

**C4 — Niveles lógicos del RC522 (sección 1.4, ampliada)**
v1 solo advertía sobre la alimentación de 3.3V. Se añade la advertencia sobre las señales SPI de 5V, la necesidad de conversor de nivel lógico y cómo verificar si el módulo propio ya lo incluye.

**C5 — `String` eliminado del código Arduino (sección 1.1, revisada)**
v1 usaba `String` en `ISensor`. Se reemplaza por `enum SensorType` y `const char*` con `PROGMEM`. Se añade `SensorType.h` y se explica el riesgo de fragmentación de heap en el ATmega328P.

**C6 — `wdt_reset()` en reconexión MQTT (secciones 1.5 y 1.7, revisadas)**
v1 tenía 3 reintentos de 2 s = hasta 6 s de bloqueo cerca del límite de 8 s del watchdog. Se añade `wdt_reset()` al inicio de cada intento y se reduce el delay entre reintentos a 1 s.

**Nota adicional para la tesis (no en plan de programación):**
RNF-07 en el documento LaTeX dice "contraseña local almacenada en la EEPROM". La arquitectura usa RFID. Actualizar el texto de RNF-07 para que diga "identificación física mediante tarjeta RFID, con UID almacenado en la EEPROM del nodo" — sin cambiar el número ni el espíritu del requisito.
