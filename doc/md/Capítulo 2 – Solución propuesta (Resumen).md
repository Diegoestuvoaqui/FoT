## Capítulo 2 – Solución propuesta (vista simplificada)

**Arquitectura**  
- Edge-first, tres capas  
- Estilos: en capas (Layered), orientado a eventos (Event-Driven), basado en componentes  

**Patrones de diseño**  
- Adapter  
- Abstract Factory  
- Observer  
- Composite  
- State  
- Memento  

**Mecanismos de diseño**  
- Persistencia de series temporales → SQLite (ACID, embebido)  
- Comunicación ligera → MQTT + broker local (Eclipse Mosquitto)  
- Autenticación física → RFID (RC522), credencial en EEPROM  
- Recuperación ante cortes eléctricos → Memento + watchdog timer + reinicio automático de servicios  
- Extensibilidad → Adapter + Abstract Factory (interfaz ISensor, SensorFactory)  
- Gestión jerárquica → Composite (Finca → Parcela → Dispositivo)  
- Notificación en tiempo real → Observer (MQTT como Subject, UI/Decision como Observers)  
- Control robusto de riego → State (Idle, Monitoring, Irrigating, Fault)  

**Tecnologías principales**  
- Microcontrolador: Arduino UNO R3  
- Sensores: DHT22, capacitivo de humedad de suelo  
- Autenticación: módulo RC522 RFID  
- Base de datos embebida: SQLite 3.x  
- Lenguaje estación base: Python 3 + Tkinter  
- Comunicación: MQTT (Eclipse Mosquitto)  
- Medios físicos: WiFi / LoRa / RF 433 MHz (prioridad según disponibilidad)  

**Conexión**  
- MQTT pub/sub sobre red local (sin Internet)  
- Tópicos: `fot/<parcela>/sensores`, `fot/<parcela>/estado`, `fot/<parcela>/control`  
- QoS 1 (entrega al menos una vez)  

**Requisitos funcionales (resumen)**  
- RF-01 a RF-13: activación manual/automática de riego, umbrales configurables, histórico de variables, gestión de parcelas y dispositivos, detección de nuevos nodos, mapa opcional  

**Atributos de calidad (RNF)**  
- RNF-01 Confiabilidad (error <5%)  
- RNF-02 Usabilidad  
- RNF-03 Eficiencia energética (autonomía ≥24h)  
- RNF-04 Mantenibilidad  
- RNF-05 Escalabilidad  
- RNF-06 Portabilidad (Windows/Linux, hardware antiguo)  
- RNF-07 Seguridad de acceso (contraseña local)  
- RNF-08 Flexibilidad (cambios sin reinicio completo)  
- RNF-09 Tolerancia a fallos (caída de un nodo no afecta al resto)  

**Restricciones (RES)**  
- RES-01: Arduino UNO como plataforma principal  
- RES-02: Componentes de bajo costo y fácil reposición local  
- RES-03: Conectividad limitada/nula → almacenamiento local + store-and-forward  
- RES-04: Alimentación inestable (baterías, apagones)  
- RES-05: Condiciones ambientales de campo (polvo, humedad, 40°C)  
- RES-06: Software de código abierto y multiplataforma  
- RES-07: Un nodo por parcela  
- RES-08: Comunicación inalámbrica (LoRa > RF 433 MHz > WiFi)  
- RES-09: Independencia total de Internet / nube  
- RES-10: Resiliencia ante cortes (watchdog, arranque automático)