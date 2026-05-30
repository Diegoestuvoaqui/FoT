## 1. Sobre la direccionalidad de las dependencias (capas)

Dices:

> *"El estilo en capas (Layered Architecture) estructura el sistema en tres niveles con dependencias unidireccionales: Nodo de Campo → Comunicación → Estación Base"*

Y preguntas: *"unidireccional pero para cambiar el estado no tendría que ser bidireccional?"*

**Respuesta:** No, no necesita ser bidireccional. El concepto de **dependencia unidireccional** en arquitectura en capas se refiere a **quién conoce a quién**, no al flujo de datos o de control.

- **Dependencia unidireccional** significa que la capa superior (Estación Base) **conoce** y **depende** de la capa inferior (Comunicación), pero la capa inferior **no conoce** a la superior. Esto es una decisión de diseño para evitar acoplamiento circular y facilitar el mantenimiento.
- **El flujo de información** (datos, comandos, estados) sí puede ser bidireccional. Por ejemplo:
  - La Estación Base envía un comando `cambiar_modo` hacia el Nodo de Campo (flujo descendente).
  - El Nodo de Campo responde con un evento `modo_cambiado` hacia la Estación Base (flujo ascendente).
  - **Pero** la implementación de esa bidireccionalidad se hace sin romper la dependencia unidireccional: la capa inferior **no llama directamente** a la superior; en lugar de eso, publica eventos (MQTT) que la capa superior escucha. Así, la capa inferior sigue sin "conocer" a la superior.

**En tu sistema FoT:**  
- El Nodo de Campo no conoce la existencia de la Estación Base. Solo publica mensajes MQTT.  
- La Estación Base sí conoce los tópicos MQTT del Nodo de Campo.  
- Eso es dependencia unidireccional, aunque el flujo de datos sea bidireccional.  
- **Cambiar el estado** (modo automático/manual) se hace mediante un comando que la Estación Base publica en un tópico que el Nodo de Campo escucha. El Nodo de Campo no "llama" a la Estación Base; solo reacciona al comando. Sigue siendo unidireccional.

Por tanto, tu texto está correcto. Si quieres ser más preciso, puedes añadir:

> "Las dependencias de compilación y conocimiento son unidireccionales (de la estación base hacia el nodo), mientras que el flujo de mensajes puede ser bidireccional gracias al patrón de publicación/suscripción."

---

