
## 1. Glosario Capítulo 1

---

## 2. Glosario Capítulo 2

---

**EEPROM** (Electrically Erasable Programmable Read-Only Memory)  
Memoria no volátil interna del microcontrolador ATmega328P (Arduino UNO) que permite almacenar configuración (umbrales, modo de operación) incluso después de un corte eléctrico.

**DHT22**  
Sensor digital de temperatura y humedad relativa de bajo costo. Rango: −40 °C a +80 °C, precisión ±0.5 °C y ±2 % HR. Se comunica por protocolo digital de un solo cable.

**RC522 RFID**  
Módulo lector/escritor de tarjetas y etiquetas RFID de 13.56 MHz. Se usa en el sistema para autenticar físicamente al agricultor (Farmer) sin necesidad de teclado en campo.

**LoRa** (Long Range)  
Tecnología de radiofrecuencia de baja potencia y largo alcance (hasta 15 km en campo abierto). Opera en bandas no licenciadas y es ideal para agricultura en zonas rurales sin cobertura celular.

**ThingSpeak**  
Plataforma de código abierto en la nube para almacenar y visualizar datos de sensores IoT. No se utiliza en el sistema FoT porque requiere conexión continua a Internet (viola RES-09).

**Centralizada en la nube**  
Arquitectura donde todos los nodos envían sus datos a un servidor remoto (nube) y las decisiones de riego se toman allí. Fue descartada por su dependencia de Internet y vulnerabilidad ante cortes eléctricos.

**Peer‑to‑peer entre nodos**  
Arquitectura donde los nodos (Arduinos) se comunican directamente entre sí sin un coordinador central. Fue descartada por la limitada capacidad de cómputo del Arduino UNO y por dificultar la gestión multi‑parcela.

**Gestión multi‑parcela**  
Capacidad del sistema de administrar varias parcelas de cultivo de forma independiente, cada una con sus propios sensores, actuadores, umbrales de riego e histórico de variables.

**Edge‑first**  
Estrategia de diseño donde la lógica de control (toma de decisiones) reside en el nodo de campo (el borde de la red) y no en un servidor central. Así, el sistema continúa funcionando aunque se pierda la conectividad con la estación base.

**MQTT** (Message Queuing Telemetry Transport)  
Protocolo ligero de mensajería basado en publicación/suscripción (pub/sub) sobre TCP/IP. Diseñado para dispositivos con recursos limitados y redes de baja confiabilidad. Su sobrecarga de cabecera es de apenas 2 bytes.

**Broker**  
Servidor central en el modelo MQTT que recibe todos los mensajes de los publicadores y los distribuye a los suscriptores según los tópicos. En el sistema FoT, el broker es Eclipse Mosquitto.

**Eclipse Mosquitto**  
Implementación de código abierto de un broker MQTT. Se ejecuta en la estación base (PC del Farmer) y no requiere conexión a Internet.

**Python/Tkinter**  
Lenguaje de programación Python 3 junto con su biblioteca estándar Tkinter para crear interfaces gráficas. Se usa en la estación base para mostrar datos, gráficos y controles.

**Snapshot**  
Captura del estado completo de configuración del sistema (umbrales, parcelas, asignación de sensores) en un momento dado. Se implementa mediante el patrón Memento.

**Interfaz Tkinter**  
Conjunto de widgets (ventanas, botones, gráficos, listas) que permite al Farmer interactuar con el sistema FoT sin necesidad de línea de comandos.

**ACID** (Atomicity, Consistency, Isolation, Durability)  
Propiedades de las bases de datos que garantizan que las transacciones se ejecuten de forma fiable. SQLite las cumple, lo que es crítico ante cortes eléctricos.

**Pub/Sub asíncrono** (Publicación/Suscripción asíncrona)  
Modelo de comunicación donde los emisores (publicadores) no envían mensajes directamente a los receptores, sino que los publican en tópicos. Los receptores (suscriptores) reciben los mensajes cuando están disponibles, sin bloquearse.

**PubSubClient**  
Biblioteca para Arduino que implementa un cliente MQTT. Permite conectar el Arduino UNO a un broker (Eclipse Mosquitto) y publicar/suscribirse a tópicos.

**MFRC522**  
Biblioteca de Arduino para controlar el módulo RC522 RFID. Proporciona funciones para leer el UID de tarjetas y etiquetas.

**UID** (Unique Identifier)  
Identificador único de 4 a 7 bytes almacenado en cada tarjeta o etiqueta RFID. Se usa en el sistema como credencial física del Farmer.

**UID almacenado en EEPROM**  
El identificador único de la tarjeta RFID autorizada se guarda en la memoria no volátil del Arduino. Al reiniciar el sistema (por un corte eléctrico), la autenticación sigue funcionando sin reprogramación.

**EEPROM del ATmega328P**  
Memoria no volátil de 1 KB dentro del microcontrolador del Arduino UNO. Se utiliza para persistir la configuración del sistema entre reinicios.

**Watchdog timer**  
Temporizador interno del microcontrolador que, si no es reiniciado periódicamente por el software, asume un bloqueo y fuerza un reinicio automático del sistema. Aumenta la resiliencia ante fallos.

---


## 1. Glosario Capítulo 3

---
