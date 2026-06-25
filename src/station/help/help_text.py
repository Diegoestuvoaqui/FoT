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
FoT es un sistema de control de riego automatizado para pequeñas parcelas.
La estación base se comunica con las placas Arduino (por USB, Bluetooth o WiFi)
y te permite monitorear y controlar el riego desde una interfaz gráfica.

PANELES DE LA APLICACIÓN
-------------------------
• Panel Principal: muestra todas las parcelas, sus lecturas en tiempo real
  y un gráfico histórico. Desde aquí podés cambiar umbrales, modo de operación
  y activar/desactivar el riego manualmente.

• Gestor de Arduinos: lista las placas detectadas (USB, WiFi o Bluetooth),
  permite asignar una placa a una parcela, actualizar el firmware y ver
  los periféricos conectados (sensores, actuadores, módulos de red).

• Exportar: guarda los datos históricos (lecturas o eventos) en formato CSV o JSON.

• Ayuda: este mismo panel.

PRIMEROS PASOS
---------------
1. Conectá un Arduino a la estación base por USB (o asegurate de que esté
   enviando datos por MQTT/WiFi).
2. En el Panel Principal, hacé clic en "+ Añadir parcela" y completá
   los campos (ID y nombre). El ID puede ser automático (parcela-XXXX).
3. Andá al Gestor de Arduinos. La placa debería aparecer en la lista.
   Seleccionala y presioná "Asignar a parcela" para vincularla.
4. Volvér al Panel Principal, seleccionár la parcela y verás sus lecturas.
   Podés cambiar el modo a "Automático" para que el sistema riegue solo
   cuando la humedad del suelo baje del umbral mínimo.

MENSAJES DE ERROR Y SOLUCIONES
-------------------------------
• "No se pudo cambiar el modo de operación."
  → Verificá que la placa esté conectada y que el broker MQTT esté activo.
• "No se pudo activar el riego."
  → La parcela puede estar en estado de fallo. Revisá el log de eventos.
• "Los umbrales deben ser números entre 0 y 100."
  → Asegurate de ingresar valores válidos (ej. 30 y 70).
• "Ya existe una parcela con ese ID o nombre."
  → Usá un identificador único, por ejemplo "parcela-0001".
• "Error al leer el sensor DHT22 en la placa FTDI_A403."
  → Verificá el cableado del sensor de temperatura/humedad.
• "No se pudo conectar con la placa en /dev/ttyUSB0."
  → Revisá que el cable USB esté firme y que tengas permisos sobre el puerto.

GLOSARIO DE TÉRMINOS
---------------------
• Sistema de control: la lógica que decide cuándo regar (antes llamada FSM).
• Modo reposo: la parcela no realiza acciones automáticas (anterior Idle).
• Modo automático: el sistema monitorea y riega según los umbrales.
• Regando: estado activo de la bomba de riego.
• Fallo del sistema: error en sensores o comunicación (Fault).
• ID de parcela: identificador único de la parcela.
• Humedad del suelo: porcentaje de agua en la tierra.
• Humedad del ambiente: humedad relativa del aire.
• Temperatura: temperatura ambiente en grados Celsius.
• Parcelas: conjunto de zonas de cultivo (antes "Finca Principal").
• Instantánea de configuración: copia de seguridad de los ajustes actuales.
• Servidor de mensajes: el broker MQTT (Mosquitto) que enruta los datos.
• Conexión en red: comunicación por WiFi/MQTT.
• Bomba de riego: actuador que controla el paso de agua.
• Umbral: valor límite para activar/desactivar el riego.
• Tiempo encendida: segundos desde el último arranque de la placa.
"""
