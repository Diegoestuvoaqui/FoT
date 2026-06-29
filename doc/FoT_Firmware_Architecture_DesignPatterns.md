
# Farm of Things (FoT) — Firmware Arduino — Documentación Técnica

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Firmware](#arquitectura-del-firmware)
3. [Requisitos Funcionales](#requisitos-funcionales)
4. [Requisitos No Funcionales](#requisitos-no-funcionales)
5. [Patrones de Diseño GoF](#patrones-de-diseño-gof)
6. [Patrones de Diseño Arquitectónicos](#patrones-de-diseño-arquitectónicos)
7. [Estructura de Carpetas](#estructura-de-carpetas)
8. [Diagrama de Clases](#diagrama-de-clases)
9. [Flujo de Ejecución](#flujo-de-ejecución)
10. [Protocolo de Comunicación](#protocolo-de-comunicación)
11. [Tecnologías y Dependencias](#tecnologías-y-dependencias)

---

## Visión General

El **Firmware FoT** es el software embebido que ejecuta en las placas Arduino (UNO, UNO R4 WiFi, etc.) del proyecto Farm of Things. Su propósito es:

- **Leer sensores** conectados a la placa (DHT11, etc.)
- **Enviar datos** en formato JSON a la estación base
- **Recibir comandos** desde la estación base (lectura manual, identificación, cambio de intervalo)
- **Soportar múltiples protocolos de comunicación**: USB Serial, Bluetooth (HC-05/06), WiFi/MQTT (UNO R4)

### Características Principales
- **Multi-protocolo**: USB Serial, Bluetooth, WiFi/MQTT
- **Multi-sensor**: Arquitectura extensible para agregar nuevos sensores
- **Protocolo JSON**: Comunicación estructurada y legible
- **Comandos en tiempo real**: Lectura manual, identificación, configuración de intervalo
- **Buffer circular**: Cola de comandos para procesamiento asíncrono
- **Auto-identificación**: El sketch reporta su tipo, versión y sensores disponibles

---

## Arquitectura del Firmware

El firmware sigue una **Arquitectura en Capas (Layered Architecture)** con separación clara entre abstracciones de hardware, lógica de negocio y protocolos de comunicación.

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE APLICACIÓN                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Sketches Concretos (DHT11Sketch, futuros...)       │   │
│  │  ├── Configuran sensores específicos                  │   │
│  │  ├── Heredan de SensorSketch                          │   │
│  │  └── Definen ID, nombre y versión del sketch           │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE DOMINIO/SKETCH                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SensorSketch (Template Method + Strategy)          │   │
│  │  ├── Gestiona colección de sensores (ISensor*)      │   │
│  │  ├── Ciclo de lectura automática por intervalo      │   │
│  │  ├── Formateo JSON de lecturas                      │   │
│  │  └── Delega comunicación a ICommunication           │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE SENSORES (Abstract)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ISensor (Interface)                                │   │
│  │  ├── DHT11Adapter (Adapter + Strategy)              │   │
│  │  │   └── Adapta librería DHT a interfaz ISensor      │   │
│  │  └── [Futuros: SoilSensor, LightSensor, etc.]       │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE COMUNICACIÓN (Abstract)          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ICommunication (Interface)                         │   │
│  │  ├── SerialCommunication    → USB (HardwareSerial)    │   │
│  │  ├── BluetoothCommunication → BT (SoftwareSerial)     │   │
│  │  ├── MQTTCommunication      → Ethernet/WiFi MQTT      │   │
│  │  └── WiFiCommunication      → WiFiS3 + MQTT (UNO R4)│   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE COMANDOS                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ICommand (Interface) + CommandParser (Factory)     │   │
│  │  ├── ReadCommand     → Ejecuta lectura inmediata    │   │
│  │  ├── IdentifyCommand → Reporta metadatos del sketch │   │
│  │  ├── IntervalCommand → Cambia intervalo de lectura  │   │
│  │  └── CommandInvoker  → Cola circular de comandos    │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE HARDWARE (Arduino)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Arduino Core (HardwareSerial, millis(), etc.)      │   │
│  │  Librerías externas: DHT, ArduinoJson, PubSubClient │   │
│  │  WiFiS3 (UNO R4), SoftwareSerial (Bluetooth)        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Principios de Diseño Aplicados
- **Inversión de Dependencias (DIP)**: `SensorSketch` depende de abstracciones (`ISensor`, `ICommunication`), no de implementaciones concretas.
- **Abierto/Cerrado (OCP)**: Nuevos sensores y protocolos se agregan sin modificar código existente.
- **Responsabilidad Única (SRP)**: Cada clase tiene una sola razón para cambiar.
- **Sustitución de Liskov (LSP)**: `DHT11Adapter` puede sustituir a cualquier `ISensor`; `SerialCommunication` puede sustituir a cualquier `ICommunication`.

---

## Requisitos Funcionales

### RF-01: Lectura de Sensores
- **RF-01.1**: El firmware debe leer sensores conectados a pines digitales/analógicos.
- **RF-01.2**: Soportar lectura de temperatura y humedad mediante DHT11.
- **RF-01.3**: Validar rangos de lectura (temperatura: -10°C a 60°C, humedad: 0% a 100%).
- **RF-01.4**: Descartar lecturas inválidas (NaN, fuera de rango).
- **RF-01.5**: Permitir múltiples sensores simultáneos (hasta 4).

### RF-02: Comunicación
- **RF-02.1**: Comunicación USB Serial a 115200 baudios (default).
- **RF-02.2**: Comunicación Bluetooth mediante SoftwareSerial (HC-05/06).
- **RF-02.3**: Comunicación WiFi/MQTT para Arduino UNO R4 WiFi.
- **RF-02.4**: Comunicación MQTT mediante Ethernet para placas con shield.
- **RF-02.5**: Formato de salida: JSON con timestamp de Arduino.
- **RF-02.6**: Reconexión automática MQTT tras desconexión.
- **RF-02.7**: Buffer circular para recepción de comandos MQTT.

### RF-03: Comandos
- **RF-03.1**: Comando `read` → Fuerza lectura inmediata y envío de datos.
- **RF-03.2**: Comando `identify` → Reporta sketch ID, nombre, versión y cantidad de sensores.
- **RF-03.3**: Comando `interval <ms>` → Cambia intervalo de lectura automática (100ms - 60s).
- **RF-03.4**: Parser de comandos JSON y texto plano.
- **RF-03.5**: Cola de comandos con capacidad máxima de 8 elementos.
- **RF-03.6**: Ejecución inmediata o encolada de comandos.

### RF-04: Ciclo de Vida del Sketch
- **RF-04.1**: `setup()` → Inicializar comunicación, sensores y reportar estado.
- **RF-04.2**: `loop()` → Lectura automática periódica según intervalo configurado.
- **RF-04.3**: Procesamiento de comandos entrantes en cada iteración del loop.
- **RF-04.4**: Watchdog timer para recuperación ante bloqueos (MQTT).

### RF-05: Formato de Datos
- **RF-05.1**: Lecturas en formato JSON: `{"ts": <millis>, "data": {"temp": {"value": 25.3, "unit": "C"}, "hum": {"value": 60.0, "unit": "%"}}, "valid": true}`
- **RF-05.2**: Identificación en formato JSON: `{"sketch": "dht11", "name": "DHT11 Sensor", "version": "1.0", "sensors": 2}`
- **RF-05.3**: Estados MQTT: `{"state": "running", "relay": false, "uptime": 12345}`

### RF-06: Extensibilidad
- **RF-06.1**: Agregar nuevos sensores implementando `ISensor`.
- **RF-06.2**: Agregar nuevos sketches heredando de `SensorSketch`.
- **RF-06.3**: Agregar nuevos protocolos implementando `ICommunication`.
- **RF-06.4**: Agregar nuevos comandos implementando `ICommand`.

---

## Requisitos No Funcionales

### RNF-01: Rendimiento
- **RNF-01.1**: Intervalo mínimo de lectura: 100ms.
- **RNF-01.2**: Intervalo máximo de lectura: 60 segundos.
- **RNF-01.3**: Procesamiento de comando en menos de 10ms.
- **RNF-01.4**: Buffer de entrada de 256 bytes para comandos MQTT.
- **RNF-01.5**: Buffer de salida JSON de 256 bytes para lecturas.

### RNF-02: Confiabilidad
- **RNF-02.1**: Reconexión automática WiFi tras desconexión (20 intentos).
- **RNF-02.2**: Reconexión automática MQTT (3 intentos con delay de 1s).
- **RNF-02.3**: Watchdog timer para reset en caso de bloqueo.
- **RNF-02.4**: Validación de lecturas para evitar datos corruptos.
- **RNF-02.5**: Cola de comandos con overflow controlado (descarte silencioso).

### RNF-03: Memoria
- **RNF-03.1**: Uso mínimo de memoria RAM (Arduino UNO tiene 2KB).
- **RNF-03.2**: Uso de ArduinoJson con documentos estáticos.
- **RNF-03.3**: Máximo 4 sensores por sketch para limitar memoria.
- **RNF-03.4**: Cola de comandos fija de 8 elementos (sin malloc dinámico excesivo).

### RNF-04: Compatibilidad
- **RNF-04.1**: Compatibilidad con Arduino UNO (ATmega328P).
- **RNF-04.2**: Compatibilidad con Arduino UNO R4 WiFi (WiFiS3).
- **RNF-04.3**: Compatibilidad con Bluetooth HC-05/06 (SoftwareSerial).
- **RNF-04.4**: Compatibilidad con shields Ethernet (PubSubClient).

### RNF-05: Mantenibilidad
- **RNF-05.1**: Código modular con separación de responsabilidades.
- **RNF-05.2**: Interfaces claras para extensión (ISensor, ICommunication, ICommand).
- **RNF-05.3**: Nomenclatura consistente y comentarios de archivo.
- **RNF-05.4**: Sin dependencias circulares entre módulos.

### RNF-06: Consumo de Energía
- **RNF-06.1**: Uso de `delay()` mínimo; preferir `millis()` para no bloquear.
- **RNF-06.2**: Desconexión WiFi/MQTT controlada para ahorro de energía (futuro).

---

## Patrones de Diseño GoF

### 1. Bridge (Puente) — Estructural

**Ubicación**: `core/communication/ICommunication.h` + implementaciones

**Propósito**: Separar la abstracción de comunicación (`SensorSketch`) de su implementación concreta (Serial, Bluetooth, WiFi, MQTT), permitiendo que ambas evolucionen independientemente.

**Implementación**:
```cpp
// Abstracción
class ICommunication {
public:
    virtual void begin() = 0;
    virtual bool available() = 0;
    virtual int read() = 0;
    virtual void send(const char* data) = 0;
    virtual bool connected() = 0;
    virtual void loop() {}
    virtual const char* name() const = 0;
};

// Implementación A: USB Serial
class SerialCommunication : public ICommunication {
    void begin() override { Serial.begin(_baud); }
    void send(const char* data) override { Serial.println(data); }
    const char* name() const override { return "usb"; }
};

// Implementación B: Bluetooth
class BluetoothCommunication : public ICommunication {
    void begin() override { _bt.begin(9600); }
    void send(const char* data) override { _bt.println(data); }
    const char* name() const override { return "bluetooth"; }
};

// Implementación C: WiFi/MQTT
class WiFiCommunication : public ICommunication {
    void begin() override { connectWiFi(); _pubSub.setServer(...); }
    void send(const char* data) override { _pubSub.publish(_topicSensores, data); }
    const char* name() const override { return "wifi"; }
};
```

**Usos**:
- `SensorSketch` opera con cualquier `ICommunication` sin conocer su implementación
- Facilita agregar nuevos protocolos (LoRa, Zigbee, etc.) sin modificar `SensorSketch`
- El sketch `main.cpp` inyecta la implementación concreta: `sketch.setCommunication(&comm)`

---

### 2. Adapter (Adaptador) — Estructural

**Ubicación**: `abstractSensors/DHT11Adapter.h`

**Propósito**: Convertir la interfaz de la librería externa `DHT` en la interfaz `ISensor` que el sistema espera.

**Implementación**:
```cpp
class ISensor {
public:
    virtual float read() = 0;
    virtual bool isValid() = 0;
    virtual const char* getName() = 0;
    virtual const char* getUnit() = 0;
};

class DHT11Adapter : public ISensor {
private:
    DHT dht;  // Librería externa
    bool _readTemp;  // true = temp, false = hum

public:
    DHT11Adapter(uint8_t pin, const char* name) : dht(pin, DHT11) {
        dht.begin();
        _readTemp = (strcmp(name, "temp") == 0);
    }

    float read() override {
        return _readTemp ? dht.readTemperature() : dht.readHumidity();
    }

    bool isValid() override {
        float val = _readTemp ? _lastTemp : _lastHum;
        return !isnan(val) && val >= minVal && val <= maxVal;
    }

    const char* getName() override {
        return _readTemp ? "temp" : "hum";
    }

    const char* getUnit() override {
        return _readTemp ? "C" : "%";
    }
};
```

**Usos**:
- Adapta librerías de terceros a la arquitectura interna
- Permite cambiar de librería DHT sin modificar `SensorSketch`
- Dos instancias del mismo adaptador para temp y hum (mismo pin, diferente comportamiento)

---

### 3. Strategy (Estrategia) — Comportamiento

**Ubicación**: `abstractSensors/ISensor.h` + adaptadores

**Propósito**: Definir una familia de algoritmos (lectura de sensores), encapsular cada uno y hacerlos intercambiables.

**Implementación**:
```cpp
// Estrategia abstracta
class ISensor {
public:
    virtual float read() = 0;
    virtual bool isValid() = 0;
    virtual const char* getName() = 0;
    virtual const char* getUnit() = 0;
};

// Estrategia concreta A: DHT11 Temperatura
DHT11Adapter tempSensor(2, "temp");

// Estrategia concreta B: DHT11 Humedad
DHT11Adapter humSensor(2, "hum");

// Contexto que usa estrategias
class SensorSketch {
    ISensor* _sensors[MAX_SENSORS];  // Array de estrategias

    void readAndSend() {
        for (uint8_t i = 0; i < _sensorCount; i++) {
            ISensor* s = _sensors[i];
            float val = s->read();        // Algoritmo específico del sensor
            if (s->isValid()) {
                data[s->getName()]["value"] = val;
                data[s->getName()]["unit"] = s->getUnit();
            }
        }
    }
};
```

**Usos**:
- `SensorSketch` itera sobre sensores sin conocer su tipo específico
- Nuevos sensores = nueva estrategia, sin modificar `SensorSketch`
- El sketch concreto (DHT11Sketch) inyecta las estrategias en `setup()`

---

### 4. Command (Comando) — Comportamiento

**Ubicación**: `core/commands/ICommand.h` + implementaciones + `CommandInvoker`

**Propósito**: Encapsular una solicitud como un objeto, permitiendo parametrizar clientes con diferentes solicitudes, encolar operaciones y soportar operaciones undo.

**Implementación**:
```cpp
// Comando abstracto
class ICommand {
public:
    virtual bool execute(SensorSketch& ctx) = 0;
    virtual const char* name() const = 0;
};

// Comando concreto: Leer sensores
class ReadCommand : public ICommand {
    bool execute(SensorSketch& ctx) override {
        ctx.readAndSend();
        return true;
    }
    const char* name() const override { return "read"; }
};

// Comando concreto: Identificar sketch
class IdentifyCommand : public ICommand {
    bool execute(SensorSketch& ctx) override {
        JsonDocument doc;
        doc["sketch"] = ctx.sketchId();
        doc["name"] = ctx.sketchName();
        doc["version"] = ctx.version();
        doc["sensors"] = ctx.getSensorCount();
        ctx.send(buf);
        return true;
    }
    const char* name() const override { return "identify"; }
};

// Comando concreto: Cambiar intervalo
class IntervalCommand : public ICommand {
    unsigned long _ms;
    bool execute(SensorSketch& ctx) override {
        ctx.setInterval(_ms);
        return true;
    }
    const char* name() const override { return "interval"; }
};

// Invocador con cola circular
class CommandInvoker {
    ICommand* _queue[MAX_COMMAND_QUEUE];
    bool enqueue(ICommand* cmd);
    bool executeNext(SensorSketch& ctx);
    static bool executeImmediate(ICommand* cmd, SensorSketch& ctx);
};
```

**Usos**:
- Desacopla el emisor del receptor de comandos
- Permite cola de comandos para procesamiento asíncrono
- Facilita agregar nuevos comandos sin modificar el parser
- `executeImmediate` para comandos que no requieren cola

---

### 5. Factory Method (Método de Fábrica) — Creación

**Ubicación**: `core/commands/CommandParser.h`

**Propósito**: Delegar la creación de objetos de comando a un método especializado, evitando `new` disperso en el código cliente.

**Implementación**:
```cpp
class CommandParser {
public:
    static ICommand* parse(const char* input) {
        if (input[0] == '{') {
            // Parseo JSON
            JsonDocument doc;
            deserializeJson(doc, input);
            const char* cmd = doc["cmd"] | "";

            if (strcmp(cmd, "read") == 0) return new ReadCommand();
            if (strcmp(cmd, "identify") == 0) return new IdentifyCommand();
            if (strcmp(cmd, "interval") == 0) {
                return new IntervalCommand(doc["ms"] | 2000);
            }
        }

        // Parseo texto plano (legacy)
        if (strcmp(input, "read") == 0) return new ReadCommand();
        if (strcmp(input, "identify") == 0) return new IdentifyCommand();
        if (strncmp(input, "interval ", 9) == 0) {
            return new IntervalCommand(atol(input + 9));
        }

        return nullptr;  // Comando desconocido
    }
};
```

**Usos**:
- Centraliza la creación de comandos
- Soporta múltiples formatos de entrada (JSON y texto plano)
- Facilita testing y mocking

---

### 6. Template Method (Método Plantilla) — Comportamiento

**Ubicación**: `core/sketches/SketchBase.h` → `SensorSketch.h` → `DHT11Sketch.h`

**Propósito**: Definir el esqueleto de un algoritmo en una clase base, delegando pasos específicos a subclases.

**Implementación**:
```cpp
// Clase base abstracta (Template Method)
class SketchBase {
public:
    virtual void setup() = 0;           // Paso 1: abstracto
    virtual void loop() = 0;            // Paso 2: abstracto

    virtual const char* sketchId() const = 0;      // Hook
    virtual const char* sketchName() const = 0;    // Hook
    virtual const char* version() const { return "1.0"; }  // Hook con default

    void send(const char* data) {       // Operación concreta
        if (_comm) _comm->send(data);
    }
};

// Clase intermedia (extiende template method)
class SensorSketch : public SketchBase {
    void setup() override {            // Implementación parcial
        send("SensorSketch::setup()");
    }

    void loop() override {              // Algoritmo definido
        unsigned long now = millis();
        if (now - _lastReadMs >= _readIntervalMs) {
            _lastReadMs = now;
            readAndSend();              // Operación concreta
        }
    }

    void readAndSend();                 // Operación concreta
    void setInterval(unsigned long ms); // Operación concreta
};

// Clase concreta (personaliza hooks)
class DHT11Sketch : public SensorSketch {
public:
    void setup() override {             // Extensión del template
        // Configurar sensores específicos
        ISensor* tempSensor = new DHT11Adapter(2, "temp");
        ISensor* humSensor = new DHT11Adapter(2, "hum");
        addSensor(tempSensor);
        addSensor(humSensor);

        SensorSketch::setup();          // Llamar al template base
    }

    void loop() override {
        SensorSketch::loop();           // Reutilizar algoritmo base
    }

    // Hooks personalizados
    const char* sketchId() const override { return "dht11"; }
    const char* sketchName() const override { return "DHT11 Sensor"; }
    const char* version() const override { return "1.0"; }
};
```

**Usos**:
- `SketchBase` define el contrato de todo sketch
- `SensorSketch` define el algoritmo de lectura periódica
- `DHT11Sketch` solo configura sensores y personaliza metadatos
- Nuevos sketches requieren mínimo código (solo hooks)

---

### 7. Singleton (Único) — Creación

**Ubicación**: `core/communication/MQTTCommunication.h`, `WiFiCommunication.h`

**Propósito**: Garantizar una única instancia de la comunicación MQTT para manejar callbacks estáticos de la librería PubSubClient.

**Implementación**:
```cpp
class MQTTCommunication : public ICommunication {
private:
    static MQTTCommunication* _instance;  // Singleton instance

    static void onMessage(char* topic, uint8_t* payload, unsigned int length) {
        if (!_instance) return;
        // Procesar mensaje usando la única instancia
        _instance->appendToBuffer(...);
    }

public:
    MQTTCommunication(Client& networkClient, ...) {
        // ...
        _instance = this;  // Registrar instancia única
    }
};

// Uso
MQTTCommunication* MQTTCommunication::_instance = nullptr;
```

**Usos**:
- Callbacks estáticos de C (PubSubClient) necesitan acceso a la instancia
- Buffer circular compartido entre callback y método `read()`
- Evita múltiples conexiones MQTT simultáneas

---

### 8. Facade (Fachada) — Estructural

**Ubicación**: `core/sketches/SensorSketch.h`

**Propósito**: Proporcionar una interfaz unificada simplificada al subsistema complejo de sensores + comunicación + JSON.

**Implementación**:
```cpp
class SensorSketch : public SketchBase {
    // Subsistemas internos complejos:
    // - Array de ISensor* (diferentes tipos)
    // - ICommunication* (diferentes protocolos)
    // - ArduinoJson (serialización)
    // - millis() (timing)

public:
    // Interfaz simplificada:
    void addSensor(ISensor* sensor);           // Agregar sensor
    void readAndSend();                          // Leer y enviar todo
    void setInterval(unsigned long ms);          // Configurar intervalo
    uint8_t getSensorCount() const;              // Info

    // El cliente (main.cpp) solo interactúa con estos métodos
    // No necesita conocer DHT, JSON, Serial, etc.
};
```

**Usos**:
- `main.cpp` solo llama a `sketch.setup()`, `sketch.loop()`, `sketch.setCommunication()`
- Oculta complejidad de ArduinoJson, timing, validación de sensores
- Facilita testing unitario del sketch

---

### 9. Observer (Observador) — Comportamiento

**Ubicación**: `core/communication/MQTTCommunication.cpp` (callback MQTT)

**Propósito**: Definir una dependencia uno-a-muchos entre objetos, donde un cambio de estado notifica a múltiples observadores.

**Implementación**:
```cpp
// Callback estático de PubSubClient (Sujeto Observable)
void MQTTCommunication::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    if (!_instance) return;

    // Filtrar solo mensajes del topic de control
    if (strncmp(topic, _instance->_topicControl, ...) != 0) return;

    // Notificar a la instancia (Observer)
    for (unsigned int i = 0; i < length; i++) {
        _instance->appendToBuffer((char)payload[i]);
    }
    _instance->appendToBuffer('\n');
}

// La instancia actúa como Observer del broker MQTT
class MQTTCommunication : public ICommunication {
    // Buffer circular que recibe datos del callback
    char _inputBuffer[INPUT_BUFFER_SIZE];

public:
    int read() override {
        // Consumir del buffer (llenado por onMessage)
        if (_inputHead == _inputTail) return -1;
        char c = _inputBuffer[_inputTail];
        _inputTail = (_inputTail + 1) % INPUT_BUFFER_SIZE;
        return c;
    }
};
```

**Usos**:
- Desacopla la recepción MQTT asíncrona del procesamiento de comandos
- El callback de la librería notifica al objeto sin acoplamiento directo
- Patrón pub/sub interno para comandos

---

### 10. State (Estado) — Comportamiento

**Ubicación**: `core/communication/MQTTCommunication.cpp`, `WiFiCommunication.cpp`

**Propósito**: Permitir que un objeto altere su comportamiento cuando su estado interno cambia.

**Implementación**:
```cpp
class WiFiCommunication : public ICommunication {
    // Estados implícitos: DISCONNECTED, WIFI_CONNECTED, MQTT_CONNECTED

    bool connected() override {
        return WiFi.status() == WL_CONNECTED && _pubSub.connected();
    }

    void loop() override {
        if (WiFi.status() != WL_CONNECTED) {
            connectWiFi();  // Estado: reconectando WiFi
        }
        if (!_pubSub.connected()) {
            connectMQTT();  // Estado: reconectando MQTT
        }
        _pubSub.loop();   // Estado: conectado y operativo
    }

    bool connectWiFi() {
        WiFi.begin(_ssid, _password);
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 20) {
            delay(500);
            attempts++;
        }
        return WiFi.status() == WL_CONNECTED;
    }

    bool connectMQTT() {
        for (uint8_t i = 0; i < 3; i++) {
            if (_pubSub.connect(_clientId)) {
                _pubSub.subscribe(_topicControl, 1);
                return true;
            }
            delay(1000);
        }
        return false;
    }
};
```

**Usos**:
- Máquina de estados para conexión WiFi/MQTT
- Transiciones automáticas entre estados de desconexión y conexión
- Comportamiento diferente según estado de conectividad

---

## Patrones de Diseño Arquitectónicos

### 1. Layered Architecture (Arquitectura en Capas)

**Descripción**: Separación del firmware en capas horizontales con dependencias unidireccionales.

| Capa | Responsabilidad | Módulos |
|------|----------------|---------|
| **Aplicación** | Configuración específica del sketch | `sketches/dht11/` |
| **Dominio/Sketch** | Ciclo de vida, lectura periódica, JSON | `core/sketches/` |
| **Sensores** | Abstracción de hardware de sensores | `abstractSensors/` |
| **Comunicación** | Abstracción de protocolos de red | `core/communication/` |
| **Comandos** | Procesamiento de comandos entrantes | `core/commands/` |
| **Hardware** | Arduino Core, librerías externas | `Arduino.h`, `DHT.h`, etc. |

**Regla de dependencia**: Las capas superiores dependen de las inferiores, nunca al revés.

---

### 2. Dependency Injection (Inyección de Dependencias)

**Descripción**: Las dependencias se inyectan desde el exterior en lugar de crearse internamente.

**Implementación**:
```cpp
// main.cpp — Composición Root
DHT11Sketch sketch;
SerialCommunication comm(SERIAL_BAUD);

void setup() {
    comm.begin();                           // Inicializar comunicación
    sketch.setCommunication(&comm);         // Inyectar comunicación
    sketch.setup();                         // Inicializar sketch
}

// SensorSketch — Recibe dependencias
class SensorSketch : public SketchBase {
    void setCommunication(ICommunication* comm) { _comm = comm; }
    void addSensor(ISensor* sensor) { _sensors[_sensorCount++] = sensor; }
};
```

**Beneficios**:
- Cambiar de Serial a Bluetooth solo requiere cambiar `main.cpp`
- Testing con mocks: inyectar `MockCommunication` y `MockSensor`
- Sin acoplamiento a implementaciones concretas

---

### 3. Plugin Architecture (Arquitectura de Plugins)

**Descripción**: El sistema identifica automáticamente el tipo de sketch y adapta el comportamiento de la estación base.

**Implementación**:
```cpp
// DHT11Sketch define su identidad
class DHT11Sketch : public SensorSketch {
    const char* sketchId() const override { return "dht11"; }
    const char* sketchName() const override { return "DHT11 Sensor"; }
};

// La estación base recibe:
// {"sketch": "dht11", "name": "DHT11 Sensor", "version": "1.0", "sensors": 2}
// Y activa el panel DHT11 automáticamente
```

**Extensibilidad**: Agregar un nuevo sensor requiere:
1. Nuevo `ISensor` en `abstractSensors/`
2. Nuevo sketch en `sketches/` que herede de `SensorSketch`
3. Panel correspondiente en la estación base (Python)

---

### 4. Circular Buffer (Buffer Circular)

**Descripción**: Estructura de datos para manejo eficiente de streams de datos con memoria fija.

**Implementación**:
```cpp
class MQTTCommunication : public ICommunication {
    static constexpr uint16_t INPUT_BUFFER_SIZE = 256;
    char _inputBuffer[INPUT_BUFFER_SIZE];
    uint16_t _inputHead;  // Escritura (callback)
    uint16_t _inputTail;  // Lectura (read())

    void appendToBuffer(char c) {
        uint16_t nextHead = (_inputHead + 1) % INPUT_BUFFER_SIZE;
        if (nextHead == _inputTail) {
            _inputOverflow = true;  // Overflow controlado
            return;
        }
        _inputBuffer[_inputHead] = c;
        _inputHead = nextHead;
    }

    int read() override {
        if (_inputHead == _inputTail) return -1;
        char c = _inputBuffer[_inputTail];
        _inputTail = (_inputTail + 1) % INPUT_BUFFER_SIZE;
        return c;
    }
};
```

**Usos**:
- Desacoplar callback MQTT asíncrono del procesamiento síncrono
- Evitar bloqueos en callback de ISR
- Memoria fija, sin fragmentación

---

## Estructura de Carpetas

```
firmware/
├── abstractSensors/          # Abstracciones de sensores (Strategy + Adapter)
│   ├── DHT11Adapter.cpp        # Adaptador DHT11 → ISensor
│   ├── DHT11Adapter.h
│   └── ISensor.h               # Interfaz de sensor (Strategy)
│
├── core/                       # Núcleo del firmware
│   ├── commands/               # Patrón Command + Factory Method
│   │   ├── CommandInvoker.cpp    # Invocador con cola circular
│   │   ├── CommandInvoker.h
│   │   ├── CommandParser.cpp     # Factory de comandos
│   │   ├── CommandParser.h
│   │   ├── ICommand.h            # Interfaz de comando
│   │   ├── IdentifyCommand.cpp   # Comando: identificar sketch
│   │   ├── IdentifyCommand.h
│   │   ├── IntervalCommand.cpp   # Comando: cambiar intervalo
│   │   ├── IntervalCommand.h
│   │   ├── ReadCommand.cpp       # Comando: leer sensores
│   │   └── ReadCommand.h
│   │
│   ├── communication/          # Patrón Bridge (ICommunication)
│   │   ├── BluetoothCommunication.cpp  # Bridge: Bluetooth
│   │   ├── BluetoothCommunication.h
│   │   ├── ICommunication.h          # Interfaz abstracta
│   │   ├── MQTTCommunication.cpp     # Bridge: MQTT (Ethernet)
│   │   ├── MQTTCommunication.h
│   │   ├── SerialCommunication.cpp   # Bridge: USB Serial
│   │   ├── SerialCommunication.h
│   │   ├── WiFiCommunication.cpp     # Bridge: WiFi + MQTT (UNO R4)
│   │   └── WiFiCommunication.h
│   │
│   └── sketches/               # Patrón Template Method
│       ├── SensorSketch.cpp      # Template: ciclo de lectura
│       ├── SensorSketch.h
│       └── SketchBase.h          # Clase base abstracta
│
└── sketches/                   # Sketches concretos (aplicación)
    └── dht11/
        ├── DHT11Sketch.cpp       # Sketch concreto: DHT11
        ├── DHT11Sketch.h
        └── main.cpp              # Punto de entrada, inyección de dependencias
```

---

## Diagrama de Clases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SKETCH BASE                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  <<abstract>> SketchBase                                            │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  # _comm: ICommunication*                                           │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  + setup() = 0                                                      │     │
│  │  + loop() = 0                                                       │     │
│  │  + sketchId() = 0                                                   │     │
│  │  + sketchName() = 0                                                   │     │
│  │  + version() { return "1.0"; }                                      │     │
│  │  + send(data)                                                       │     │
│  │  + setCommunication(comm)                                           │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                    △                                         │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  <<abstract>> SensorSketch                                            │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  # _sensors: ISensor*[MAX_SENSORS]                                  │   │
│  │  # _sensorCount: uint8_t                                            │   │
│  │  # _lastReadMs: unsigned long                                       │   │
│  │  # _readIntervalMs: unsigned long                                   │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  + setup() override                                                 │   │
│  │  + loop() override      { Template Method }                         │   │
│  │  + addSensor(sensor)                                                │   │
│  │  + readAndSend()                                                    │   │
│  │  + setInterval(ms)                                                  │   │
│  │  + getSensorCount()                                                 │   │
│  │  + sketchId() { return "sensor"; }                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    △                                         │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DHT11Sketch                                                          │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  + setup() override     { Configura DHT11Adapter x2 }               │   │
│  │  + loop() override      { SensorSketch::loop() }                    │   │
│  │  + sketchId() override  { return "dht11"; }                         │   │
│  │  + sketchName() override{ return "DHT11 Sensor"; }                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              SENSORES (Strategy)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  <<interface>> ISensor                                                │     │
│  │  + read(): float                                                      │     │
│  │  + isValid(): bool                                                    │     │
│  │  + getName(): const char*                                             │     │
│  │  + getUnit(): const char*                                             │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                    △                                         │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DHT11Adapter                                                         │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - dht: DHT         { Librería externa }                            │   │
│  │  - pin: uint8_t                                                       │   │
│  │  - _readTemp: bool    { true=temp, false=hum }                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  + DHT11Adapter(pin, name)                                          │   │
│  │  + read() override                                                    │   │
│  │  + isValid() override                                                 │   │
│  │  + getName() override                                                 │   │
│  │  + getUnit() override                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMUNICACIÓN (Bridge)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  <<interface>> ICommunication                                         │     │
│  │  + begin()                                                            │     │
│  │  + available(): bool                                                  │     │
│  │  + read(): int                                                        │     │
│  │  + send(data)                                                         │     │
│  │  + connected(): bool                                                    │     │
│  │  + loop()                                                             │     │
│  │  + name(): const char*                                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         △                    △                    △                    △       │
│         │                    │                    │                    │       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │SerialComm    │   │BluetoothComm │   │MQTTComm      │   │WiFiComm      │   │
│  │- _baud: long │   │- _bt: SoftSer│   │- _pubSub     │   │- _pubSub     │   │
│  │+ name()="usb"│   │+ name()="bt" │   │+ name()="mqtt"│   │+ name()="wifi"│   │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMANDOS (Command)                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  <<interface>> ICommand                                               │     │
│  │  + execute(ctx): bool                                                 │     │
│  │  + name(): const char*                                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         △                    △                    △                            │
│         │                    │                    │                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │ ReadCommand   │   │IdentifyCmd   │   │IntervalCmd   │                   │
│  │+ execute()    │   │+ execute()    │   │- _ms: ulong  │                   │
│  │+ name()="read"│   │+ name()="id"  │   │+ execute()    │                   │
│  └──────────────┘   └──────────────┘   └──────────────┘                   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  CommandParser                                                        │     │
│  │  + parse(input): ICommand*    { Factory Method }                    │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  CommandInvoker                                                       │     │
│  │  - _queue: ICommand*[8]                                               │     │
│  │  - _head, _tail, _count: uint8_t                                    │     │
│  │  + enqueue(cmd): bool                                                 │     │
│  │  + executeNext(ctx): bool                                             │     │
│  │  + executeImmediate(cmd, ctx): bool                                 │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Flujo de Ejecución

### Inicialización (setup)
```
main.cpp::setup()
    ├── SerialCommunication::begin()      → Inicializa HardwareSerial
    ├── sketch.setCommunication(&comm)    → Inyecta comunicación
    └── DHT11Sketch::setup()
        ├── new DHT11Adapter(2, "temp")    → Crea sensor temperatura
        ├── new DHT11Adapter(2, "hum")     → Crea sensor humedad
        ├── addSensor(temp)                → Registra en array
        ├── addSensor(hum)                 → Registra en array
        └── SensorSketch::setup()          → Mensaje de bienvenida
```

### Ciclo Principal (loop)
```
main.cpp::loop()
    ├── DHT11Sketch::loop()
    │   └── SensorSketch::loop()
    │       └── if (millis() - _lastReadMs >= _readIntervalMs)
    │           └── readAndSend()
    │               ├── for each ISensor:
    │               │   ├── sensor->read()       → DHT11Adapter::read()
    │               │   ├── sensor->isValid()    → Validar rango
    │               │   └── ArduinoJson → data[sensor->getName()]
    │               └── _comm->send(json)        → Serial/MQTT/WiFi
    │
    └── Procesar comandos entrantes
        ├── comm.available() → ¿Hay datos?
        ├── comm.read() → Acumular en buffer hasta '\n'
        ├── CommandParser::parse(buffer) → Factory
        │   └── new ReadCommand() / IdentifyCommand() / IntervalCommand()
        └── CommandInvoker::executeImmediate(cmd, sketch)
            └── cmd->execute(sketch)
                ├── ReadCommand → sketch.readAndSend()
                ├── IdentifyCommand → sketch.send(metadata JSON)
                └── IntervalCommand → sketch.setInterval(ms)
```

---

## Protocolo de Comunicación

### Formato de Salida (Arduino → Estación Base)

#### Lectura de Sensores
```json
{
  "ts": 12345,
  "data": {
    "temp": {
      "value": 25.3,
      "unit": "C"
    },
    "hum": {
      "value": 60.0,
      "unit": "%"
    }
  },
  "valid": true
}
```

#### Identificación del Sketch
```json
{
  "sketch": "dht11",
  "name": "DHT11 Sensor",
  "version": "1.0",
  "sensors": 2
}
```

#### Estado (MQTT)
```json
{
  "state": "running",
  "relay": false,
  "uptime": 12345
}
```

### Formato de Entrada (Estación Base → Arduino)

#### Comandos JSON
```json
{"cmd": "read"}
{"cmd": "identify"}
{"cmd": "interval", "ms": 5000}
```

#### Comandos Texto Plano (Legacy)
```
read
identify
interval 5000
```

### Topics MQTT

| Topic | Dirección | Contenido |
|-------|-----------|-----------|
| `fot/<parcelaId>/sensores` | Arduino → Broker | Lecturas JSON |
| `fot/<parcelaId>/estado` | Arduino → Broker | Estado del sketch |
| `fot/<parcelaId>/control` | Broker → Arduino | Comandos JSON |

---

## Tecnologías y Dependencias

### Core Arduino
| Tecnología | Propósito |
|------------|-----------|
| Arduino.h | Core de Arduino (millis(), Serial, etc.) |
| avr/wdt.h | Watchdog timer |

### Librerías Externas
| Librería | Versión | Propósito |
|----------|---------|-----------|
| DHT | Latest | Lectura de sensor DHT11/DHT22 |
| ArduinoJson | v7+ | Serialización/deserialización JSON |
| PubSubClient | Latest | Cliente MQTT |
| WiFiS3 | Built-in | WiFi para Arduino UNO R4 |
| SoftwareSerial | Built-in | Bluetooth HC-05/06 en UNO |

### Hardware Soportado
| Placa | Protocolos | Notas |
|-------|-----------|-------|
| Arduino UNO (ATmega328P) | USB Serial, Bluetooth | 2KB RAM, 32KB Flash |
| Arduino UNO R4 WiFi | USB Serial, WiFi/MQTT | WiFiS3, más RAM |
| Arduino + Ethernet Shield | USB Serial, MQTT | PubSubClient + Ethernet |

---

## Glosario de Términos

| Término | Definición |
|---------|------------|
| **Sketch** | Programa Arduino que hereda de `SketchBase` |
| **Sensor** | Periférico de medición adaptado a `ISensor` |
| **Bridge** | Protocolo de comunicación adaptado a `ICommunication` |
| **Parcela** | Identificador lógico de la ubicación (usado en topics MQTT) |
| **Comando** | Orden enviada desde la estación base al Arduino |
| **Lectura** | Valor capturado por un sensor en un momento dado |
| **Intervalo** | Tiempo entre lecturas automáticas (ms) |
| **Watchdog** | Timer de hardware que resetea el Arduino si se bloquea |
| **Buffer Circular** | Estructura de datos FIFO de tamaño fijo |

---

## Conclusiones

El firmware de Farm of Things demuestra una aplicación práctica de múltiples patrones de diseño GoF para resolver un problema real de IoT embebido:

1. **Bridge + Strategy** permiten soportar múltiples protocolos de comunicación y tipos de sensores con una interfaz unificada.

2. **Command + Factory Method** desacoplan la recepción de comandos de su ejecución, facilitando la extensión.

3. **Template Method** define el algoritmo de lectura periódica mientras permite personalización por sketch.

4. **Adapter** integra librerías de terceros sin acoplar la arquitectura interna.

5. **Dependency Injection** permite cambiar protocolos y sensores sin modificar el código del sketch.

6. **Circular Buffer** maneja la asincronía de callbacks MQTT en memoria fija.

El diseño está preparado para extensión: nuevos sensores, protocolos o comandos pueden agregarse respetando las interfaces existentes y los principios SOLID, incluso en un entorno con recursos limitados como Arduino UNO (2KB RAM, 32KB Flash).

---

*Documento generado para el firmware Farm of Things (FoT) — Arduino*
*Arquitectura: Layered + Dependency Injection + Plugin*
*Patrones GoF: Bridge, Adapter, Strategy, Command, Factory Method, Template Method, Singleton, Facade, Observer, State*
