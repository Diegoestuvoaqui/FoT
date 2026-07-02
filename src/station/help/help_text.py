"""
help/help_text.py
Contenido de la ayuda en español.
Se importa como una cadena desde HelpPanel.
"""

HELP_TEXT = """
============================================================
                    FoT — Farm of Things
============================================================

INTRODUCCIÓN
------------
FoT es un sistema de monitoreo de sensores para placas Arduino.
La estación base se comunica con las placas (por USB, Bluetooth o WiFi)
y te permite visualizar datos en tiempo real desde una interfaz gráfica.

PANELES DE LA APLICACIÓN
-------------------------
• Panel DHT11: muestra todas las placas con sketch DHT11, sus lecturas
  en tiempo real y un historial de datos.

• Gestor de Arduinos: lista las placas detectadas (USB, WiFi o Bluetooth),
  permite registrar placas, actualizar el firmware y ver
  los periféricos conectados (sensores, módulos de red).

• Ayuda: este mismo panel.

PRIMEROS PASOS
---------------
1. Conectá un Arduino a la estación base por USB (o asegurate de que esté
   enviando datos por MQTT/WiFi).
2. En el Gestor de Arduinos, la placa debería aparecer en la lista.
   Seleccionala y presioná "Conectar" para iniciar la comunicación.
3. Volvé al Panel DHT11, seleccioná la placa y verás sus lecturas
   de temperatura y humedad en tiempo real.

MENSAJES DE ERROR Y SOLUCIONES
-------------------------------
• "Error al leer el sensor DHT11 en la placa..."
  → Verificá el cableado del sensor de temperatura/humedad.
• "No se pudo conectar con la placa en /dev/ttyUSB0."
  → Revisá que el cable USB esté firme y que tengas permisos sobre el puerto.
• "Sin conexión con el broker MQTT."
  → Verificá que Mosquitto esté activo en localhost:1883.
• "No se pudo cargar el firmware."
  → Revisá que la placa esté en modo bootloader y que avrdude esté instalado.

GLOSARIO DE TÉRMINOS
---------------------
• Sketch: programa cargado en el Arduino (ej: DHT11, futuros sensores).
• Board / Placa: dispositivo Arduino físico.
• Sensor: periférico que mide magnitudes (temperatura, humedad, etc.).
• Lectura: valor actual capturado por un sensor.
• Servidor de mensajes: el broker MQTT (Mosquitto) que enruta los datos.
• Conexión en red: comunicación por WiFi/MQTT.
• Firmware: código compilado cargado en la placa Arduino.
• Instantánea de configuración: copia de seguridad de los ajustes actuales.
"""
