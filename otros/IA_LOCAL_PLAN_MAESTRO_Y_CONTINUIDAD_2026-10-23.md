# IA LOCAL — DOSIER MAESTRO DE CONTINUIDAD Y PLAN DE RECONCILIACIÓN

**Proyecto:** `ia_local`, aplicación de inteligencia artificial reutilizable para Django.  
**Anfitrión de desarrollo:** Condocdat (`~/max/projects/condocdat`).  
**Anfitrión de portabilidad previsto:** STIHL; posteriormente otros sistemas Django (Nómina, talleres, etc.).  
**Fecha de corte:** 23 de octubre de 2026.  
**Estado:** diseño ARC001–ARC006 aprobado; todavía **NO** se han implementado esas seis especificaciones. La ruta D06 de conteo simple fue probada, pero no está integrada en la entrada visual habitual.  
**Propósito del documento:** transferir contexto técnico, criterios arquitectónicos, decisiones, incidentes y pruebas a un nuevo chat sin perder la continuidad del desarrollo.

> **INSTRUCCIÓN PARA UN NUEVO CHAT:** Lee íntegramente este documento y úsalo como hoja de ruta. No propongas comenzar de cero, no des por completadas ARC001–ARC006, no desactives indiscriminadamente C05 y no introduzcas reglas particulares de Condocdat en el núcleo de `ia_local`. Antes de cualquier modificación, inspecciona la versión real del código, confirma el punto de entrada afectado y define una prueba de aceptación ejecutada desde la interfaz. Entrega mini-especificaciones concretas, cambios localizados y comandos reproducibles; preserva código y datos existentes.

---

## 1. Visión y objetivos irrenunciables

El producto **no** pretende memorizar preguntas y respuestas específicas. Pretende interpretar lenguaje natural para consultar, de modo controlado, el ORM del proyecto Django donde se instala.

Tres objetivos expresos del usuario:

1. **Máxima independencia del proyecto anfitrión.** El núcleo no debe conocer por código nombres propios de aplicaciones, modelos, tablas, campos o valores (por ejemplo `rdi.RDIRecord`, `documents.CorreoEnviado`, `status`, `ABIERTA`). Cualquier conocimiento de negocio especial vive en metadatos, configuración declarativa o adaptadores del anfitrión.
2. **Máximo conocimiento aprovechable del negocio anfitrión.** Descubrir de Django modelos, campos, tipos, relaciones, choices, nombres `verbose_name`, permisos; enriquecer con vocabulario, sinónimos, datos permitidos y reglas declarativas. Nunca inferir como certeza reglas de negocio que no estén sustentadas.
3. **Capas colaborativas para Ollama/Qwen y el ORM correcto.** HOST, BRIDGE, QUERY, LLM y FINAL aportan conocimiento e interpretación, sin perder restricciones de la pregunta; un mecanismo final debe autorizar la consulta antes de ejecutarla.

**Regla funcional transversal:** `/ia/index/` (template `ia_local/templates/ia_local/index.html`) y `/ia/diagnostico/` (template `ia_local/templates/ia_local/diagnostico.html`) deben utilizar el **mismo servicio canónico de interpretación, validación, autorización y ejecución**. Solo puede variar cómo se muestra el resultado y cuánto detalle de trazabilidad se presenta. La ruta de diagnóstico no debe eludir permisos ni ejecutar planes que la interfaz principal rechazaría.

**Regla de seguridad:** un plan ORM estructuralmente válido no demuestra por sí solo que Qwen haya preservado todas las condiciones de la pregunta. No autorizar ejecuciones cuando falta cobertura semántica, restricciones quedan sin resolver o el modelo/campo/valor no están permitidos.

**Regla de desarrollo:** no dar por terminada una funcionalidad basándose únicamente en un script de consola o en tests unitarios del componente. Debe recorrer la entrada HTTP real; además, verificar ambos frontends y un banco de preguntas históricas.

---

## 2. Contexto tecnológico y repositorios

- Proyecto Python/Django `condocdat`, con PostgreSQL como origen de datos del anfitrión.
- App portable `ia_local` dentro de Condocdat en esta etapa; primero madurar allí y después comprobar su portabilidad instalándola en STIHL sin modificar el núcleo.
- LLM local con Ollama, modelo registrado en los diagnósticos: `qwen3:4b-instruct-2507-q4_K_M`.
- El LLM propone interpretaciones estructuradas; Django/HOST decide la estructura permitida y el acceso al ORM.
- Componentes mayores identificados:
  - `ia_local/services/host/`: catálogo/descubrimiento, resolución de entidades, validación y ejecución de planes, sesiones y expedientes.
  - `ia_local/services/bridge/`: interpretación y composición determinista.
  - `ia_local/services/query/`: lógica AND/OR, agrupaciones, ordenamiento, fechas, relaciones, agregación.
  - `ia_local/services/llm/`: extracción, interpretación y consolidación Qwen, auditorías/cobertura.
  - `ia_local/services/final/`: orquestación, contratos, ejecución y formateo.
  - `ia_local/services/semantica/`: aliases, vocabulario.
  - `ia_local/models.py` y `ia_local/migrations/0009_iaexpedienteconsulta.py`: persistencia del expediente.
  - `ia_local/views.py`, `ia_local/urls.py`, plantillas y `ia_local/views_desambiguacion.py`: interfaces y rutas.

**Fuentes de comparación entregadas por el usuario:** `ia_local-anterior.zip` (versión funcional histórica) y `ia_local-actual.zip` (nueva versión). Cuando un nuevo chat tenga acceso a los adjuntos, es conveniente volver a utilizarlos para contrastar cambios; la auditoría anterior comparó su código estáticamente. **No presupongas que el repositorio presente en el nuevo chat es idéntico a alguno de esos ZIP**.

**Git:** `main` estaba sincronizada con `origin/main` antes del proceso de commit; se preparó un staging de `.gitignore` y `ia_local/`. Se detectaron advertencias `git diff --cached --check` de finales de línea/espacios y se dieron instrucciones para corregirlas. **No hay confirmación en esta conversación de que se haya realizado el commit ni el push.** Verificar `git status`, `git log -1`, `git diff --cached --check` antes de tomar decisiones.

---

## 3. Arquitectura de referencia (objetivo de ARC)

```text
Pregunta original + identidad/sesión/permisos
            |
            v
Entrada canónica — ARC001
            |
            v
HOST: contexto autorizado del negocio
(modelos, campos, relaciones, datos permitidos, vocabulario, reglas)
            |
            v
Interpretación y composición
  +-- BRIDGE / QUERY deterministas
  +-- LLM Ollama/Qwen complementario cuando sea necesario
            |
            v
Contrato semántico común — ARC002
(requisitos originales + procedencia + propuesta interpretada)
            |
            v
Certificación HOST — ARC003
(entidad, intención, restricciones, lógica, relaciones,
 orden, límites, proyección, permisos; evidencia de cobertura)
            |
            v
FINAL — ARC004
(autorización única, aclaración o rechazo)
            |
            v
Ejecutor HOST autorizado -> ORM Django -> respuesta canónica
            |
            +--> /ia/index/ (presentación sencilla)
            +--> /ia/diagnostico/ (misma decisión + trazabilidad)
            +--> API pertinente (mismo motor)

ARC005 = regresión histórica y E2E sobre interfaces.
ARC006 = portabilidad verificable en un segundo anfitrión.
```

**Nota:** HOST es transversal; ofrece conocimiento antes y durante la interpretación y vuelve a validar antes de ejecutar. Qwen **no** accede directamente al ORM y **no** es la etapa que autoriza. FINAL no debe otorgar ejecución solamente por un `plan_validado=True` estructural.

---

## 4. Diagnóstico comparativo: anterior vs. actual

Hallazgos reportados en la auditoría de las dos versiones:

- La mayor parte del núcleo BRIDGE/QUERY siguió presente; se añadieron módulos de certificación, expedientes y cobertura.
- Se identificaron entradas visuales potencialmente divergentes: `consulta_ia()` hacia `_ejecutar_consulta_ia()`/`procesar_pregunta()` del router HOST, y `consulta_ia_json()` hacia `responder_consulta()` (FINAL004 → FINAL003 → FINAL002). Verificar mapeos concretos de URL y JavaScript en el código real. Diagnóstico e interfaz principal podían tomar caminos distintos.
- En versión anterior, FINAL002 autorizaba fallback LLM cuando HOST validaba el plan estructural. En versión actual, añadió barrera **C05**: rechaza como `consulta_llm_pendiente_cobertura` hasta disponer de certificación semántica integral.
- Los certificadores D06 son funcionales en pruebas directas pero **no están conectados automáticamente** a FINAL y a ambas interfaces.
- `llm/cobertura_semantica.py` puede detectar riesgos, pero incluye `certificacion_integral_no_disponible`; aún no otorga certificación positiva general.
- FINAL001 recorre componentes deterministas y acepta el primer resultado favorable; el `ok=True` de un componente no prueba necesariamente que se hayan cubierto todas las condiciones de la pregunta.
- El modelo de ejecución actual es más conservador que el anterior; se han observado regresiones de experiencia y funcionalidad. **No volver íntegramente al anterior ni desbloquear indiscriminadamente C05.**

**Interpretación de este diagnóstico:** la principal desviación es **integración incompleta**, no pérdida de interpretación ni necesidad de otro motor ORM.

---

## 5. Incidente de referencia: «cuantas rdi estan abiertas»

Diagnóstico real observado desde FINAL004:

- Pregunta: `cuantas rdi estan abiertas`.
- FINAL001: `consulta_no_resuelta` y, para BRIDGE003, `operador_no_resuelto`.
- Fallback Qwen (`IA-LLM001`): `ok=True`, `plan_validado=True`, `llm_invocado=True`.
- HOST descubrió la entidad `rdi.RDIRecord` por catálogo y datos, resolvió el campo `status`, reconoció valor `ABIERTA` y validó el plan.
- Plan propuesto y validado:

```json
{
  "modelo": "rdi.RDIRecord",
  "operacion": "contar",
  "filtros": [{"campo": "status", "operador": "exact", "valor": "ABIERTA"}],
  "orden": [],
  "limite": null,
  "condiciones_no_resueltas": []
}
```

- FINAL002: `ok=False`, `estado=consulta_llm_pendiente_cobertura`, `ejecutable=False`, razón: estructura HOST validada pero sin certificación semántica integral LLM008.
- FINAL003: `contrato_no_disponible`.
- FINAL004: `respuesta_error`, texto poco informativo «FINAL002 no pudo construir un contrato válido».

**Conclusión técnica:** el sistema interpretó y validó un plan compatible con la pregunta, **pero fue bloqueado por política**, no porque Qwen dejara de conocer el negocio. El plan aparentemente correcto no constituye por sí solo una prueba de cobertura integral. Hay que recuperar esa capacidad mediante el certificado común y corregir el mensaje al usuario distinguiendo «no entendida» de «interpretada, pero no autorizada».

---

## 6. Qué funcionó y qué NO prueba todavía

### Validaciones de código existentes

Resultados observados, ejecutados en Condocdat:

- `python manage.py ia_query_regression` → **15/15**.
- `python manage.py ia_final_close` → **11/11**.
- `python manage.py test ia_local.tests.test_llm008_cobertura ia_local.tests.test_llm008_verificador` → **8/8**.
- `python manage.py check` → sin errores.
- `python manage.py makemigrations --check --dry-run` → sin cambios pendientes.
- `python manage.py showmigrations ia_local` → `0001` a `0009` aplicadas, incluida `0009_iaexpedienteconsulta`.

Estas pruebas **no garantizan** que todas las preguntas históricas vuelvan a responder desde las dos interfaces ni que todas las rutas deterministas cubran la semántica completa.

### Ruta D06 de conteo simple certificada

- `host/certificador_expediente.py`: certificado diagnóstico/negativo general.
- `host/certificador_conteo_simple.py` (D06-C1): certificación positiva **solamente** para plantilla estricta de conteo sin filtros, con verificación independiente del modelo por HOST.
- `host/contrato_conteo_certificado.py` (D06-C2): reconstruye en servidor plan `contar`, filtros y orden vacíos, `limite=None`, `condiciones_no_resueltas=[]`, vuelve a validar con HOST.
- `final/ejecucion_certificada.py` (D06-C3): servicio de ejecución desde expediente `request, identificador, version`; fila bloqueada con transacción PostgreSQL, marca expediente `COMPLETADO`, incrementa versión y llama al ejecutor HOST.
- D06-C4: ensayo de 10 verificaciones aprobadas: versión obsoleta, usuario ajeno, sesión ajena, caducidad, pregunta con filtro rechazada, fallo simulado, rollback, exclusión concurrente, estado final y segundo consumo rechazado. Una de dos solicitudes paralelas ejecutó; otra fue rechazada. Resultado de lectura: **888 documentos** en aquel momento (dato variable, no test fijo).

**Límites importantes:**

1. La ejecución D06-C3 se invoca separadamente: no demuestra integración HTTP principal.
2. D06-C1 no autoriza preguntas con filtros como «rdi abiertas».
3. Un error que revierte la transacción puede dejar expediente `ABIERTO` y reintentable; aceptable en conteo de solo lectura, no asumirlo suficiente para operaciones con efectos externos.
4. Para esta fase, mantener operaciones estrictamente de lectura y sin modificaciones a datos de negocio.
5. El ensayo D06-C4 se ejecutó como script temporal y luego se eliminó durante la limpieza de residuos; no equivale necesariamente a test permanente versionado.

### Bloqueo C05 — decisión vigente

Está localizado en `ia_local/services/final/contrato_respuesta.py`: fallback LLM sin cobertura acreditada produce `consulta_llm_pendiente_cobertura`, `ejecutable=False`. No quitarlo globalmente. ARC003/ARC004 deberán permitir autorización **selectiva** con evidencia y permisos, manteniendo rechazo seguro cuando falte cobertura.

---

## 7. Batería histórica obligatoria (formulaciones preservadas)

Las siguientes preguntas provienen de pruebas compartidas desde las interfaces visuales y de ejemplos adicionales del usuario. **Conservar exactamente las formulaciones, incluso errores ortográficos; registrar resultado anterior/actual y expectativa validada por el negocio.** No afirmar que todas funcionaron históricamente: algunos registros ya mostraban resultados divergentes o fallos.

| ID | Pregunta original | Cobertura exigida |
|---|---|---|
| H01 | `cuantas rdi estan abiertas` | conteo con filtro de estado |
| H02 | `cuantas rdi de civil estan abiertas` | conteo, estado + disciplina, AND |
| H03 | `hay alguna rdi de fire protection que este abierta` | existencia, dos restricciones |
| H04 | `cuales son los ultimos correos enviados` | listado, orden temporal, límite de política si no explícito |
| H05 | `que asunto tienen los ultimos 10 correos enviados` | proyección `asunto`, orden, límite 10 |
| H06 | `lista los ultmos 5 correos enviados` | typo «ultmos», listado, orden descendente, límite 5 |
| H07 | `lista todos los correos enviados` | totalidad solicitada, política de paginación/presentación sin ocultar que hay más |
| H08 | `cual fue el ultimo dayli report` | sinónimo/typo, documento reciente |
| H09 | `en que documento hay informacion del procedimiento para trabajo seguro en altura` | búsqueda documental/contenido, entidad |
| H10 | `dame la lista de las RDI que aun estan abiertas` | listado y filtro |
| H11 | `hay alguna RDI de civil que no este cerrada` | existencia, disciplina y negación |
| H12 | `en que fecha se tuvo respuesta de odata para el procedimiento REVISIÓN Y MANTENCIÓN EN TERRENO` | relaciones/referencia/fecha |
| H13 | `cual fue el reporte diario` | variación lingüística; posible ambigüedad |

**Dos evidencias visuales concretas:**

- `lista los ultmos 5 correos enviados`: `/ia/index` respondió que no podía determinar con seguridad la consulta; `/ia/diagnostico` sí ejecutó un plan para `documents.CorreoEnviado`, ordenado por `enviado_at desc`, limitado a cinco. Esto demuestra divergencia de recorridos o políticas.
- `lista todos los correos enviados`: `/ia/index` mostró «Se encontraron 20 registros de CorreoEnviado»; el diagnóstico interpretó la totalidad solicitada (`limite=None`), pero la presentación devolvía una lista extensa. Diferenciar total real de paginación y límite de presentación.

**Pruebas negativas imprescindibles:** filtro omitido, segundo filtro omitido, negación invertida, OR convertido a AND, relación inventada, fecha ignorada, orden/límite equivocados, entidad ambigua y campo de salida incorrecto. La expectativa puede ser «bloqueada/solicitar aclaración» cuando no haya correspondencia legítima.

---

## 8. Especificaciones aprobadas para la siguiente etapa

**Estado global:** ARC001–ARC006 acordadas como **plan**, pendientes de implementación y aceptación. ARC005 debe comenzar a instrumentarse tempranamente y crecer con cada fase, no esperar hasta el final.

### ARC001 — Entrada canónica y paridad de interfaces

**Objetivo:** una sola puerta lógica de consulta para `/ia/index/`, `/ia/diagnostico/` y API pertinente.

**Problema:** entradas HTTP distintas invocan motores distintos (`procesar_pregunta` frente a `responder_consulta`), causando decisiones dispares.

**Acciones:**

1. ARC001-A: inventariar mapeos reales de `urls.py`, views, JS/formularios, funciones `consulta_ia`, `consulta_ia_json`, entrada diagnóstica, router HOST, FINAL004 y FINAL003. Confirmar firmas/efectos antes de cambiar.
2. ARC001-B: definir contrato de servicio canónico, por ejemplo `procesar_consulta_canonica(request, pregunta, contexto=None)`, con pregunta íntegra, identidad, sesión, permisos, ID de consulta, origen de interpretación, estado, decisión/certificado, plan, resultado y trazabilidad.
3. ARC001-C: conectar ambas interfaces al servicio canónico. Formateadores distintos pueden ver el mismo resultado; diagnóstico no debe saltarse autorización ni ejecutar otra consulta al mostrar trazabilidad de ejecución existente. Si se introduce «solo diagnóstico», debe ser **sin ejecución** explícita.
4. ARC001-D: tests HTTP Django Test Client sobre el mismo contexto de usuario; comprobar misma decisión/plan y no duplicación de ejecución. Conservar contratos públicos cuando sea viable.

**Restricción de fase:** no cambiar Qwen, los componentes QUERY ni la barrera C05 salvo adaptación mínima imprescindible y probada.

**Cierre:** igual interpretación, certificación y autorización desde ambos frontends para idéntica pregunta/identidad/contexto. Tests QUERY 15/15 y FINAL 11/11 siguen pasando.

### ARC002 — Contrato semántico común, versionado y trazable

**Objetivo:** representar íntegramente requisitos de la pregunta, sin depender de qué motor interpretó.

**Modelo lógico:** intención operacional; entidad; requisitos atómicos de filtros; AND/OR/NOT y paréntesis; relaciones/alcance; fechas absolutas/relativas; orden; límite; selección de campos de salida (proyección); ambigüedades; procedencia/evidencia; requisitos introducidos por políticas (no confundir con expresados por usuario).

**Acciones:**

1. Diseñar esquema versionado, determinista y validable (estructura/JSON schema o dataclasses) con ID estable por requisito.
2. Conservar spans de texto original para ligar cada requisito a la pregunta, sin perder negaciones, plurales, typos ni expresiones temporales.
3. Mapear resultados existentes BRIDGE/QUERY/LLM hacia contrato común mediante adaptadores; no reescribir todos los motores.
4. Diferenciar «requisito extraído», «propuesta LLM», «campo/valor confirmado HOST», «política añadida», «pendiente».
5. Usar los casos H01–H13 para probar representación, especialmente proyección `asunto`, totalidad `todos`, existencia `hay alguna`, `últimos`, negaciones y múltiples filtros.

**Componentes candidatos:** `llm/extraccion_semantica.py`, `llm/auditoria_semantica.py`, `llm/trazabilidad_compuesta.py`, `llm/consolidacion_semantica.py`, `bridge/compositor_sem_host.py`, `query/condiciones_and.py`, `query/condiciones_or.py`, `query/grupos_logicos.py`.

**Cierre:** contrato captura cada requisito obligatorio de la pregunta; los desconocidos aparecen como `pendientes`, nunca se eliminan silenciosamente. No hay reglas codificadas para Condocdat en el núcleo.

### ARC003 — Certificación de cobertura y significado por HOST

**Objetivo:** demostrar que un plan permitido representa los requisitos originales (no solo que sus campos existan).

**Acciones:**

1. Verificar modelo/entidad permitidos y correspondencia sustentada con la pregunta.
2. Verificar operación real: `contar`, `listar`, `existe` (o semántica equivalente que respete la pregunta).
3. Asociar **cada** condición, operador y valor con su requisito original y evidencia autorizada del HOST.
4. Validar árbol lógico, negaciones, relaciones y alcance, fechas, orden, límite, proyección y políticas.
5. Comprobar permisos de usuario y ámbito, y distinguir plan íntegro frente a plan parcialmente válido.
6. Certificado con estado explícito: `certificado`, `cobertura_completa`, requisitos verificados/pendientes, incompatibilidades, plan HOST reconstruido y autorización. No confiar en un JSON de certificación entregado por el cliente.
7. Generar solicitudes de aclaración concretas cuando corresponda.

**Reutilizar:** `host/certificador_expediente.py`, `host/certificador_conteo_simple.py`, `host/contrato_conteo_certificado.py`, `host/validador_plan_datos.py`, `host/expediente_consulta.py`, `llm/cobertura_semantica.py`, `llm/trazabilidad_compuesta.py`.

**Cierre:** capacidad de emitir certificados positivos verificables para los casos cubiertos y rechazo de equivalencias falsas. Prueba crítica: para H02, un plan con solo filtro de estado, sin `civil`, DEBE rechazarse. **No declarar cobertura universal automática; la certificación positiva se expande por capacidades verificadas.**

### ARC004 — Única autorización/despacho FINAL

**Objetivo:** cerrar la brecha entre los nuevos certificadores y las rutas reales de FINAL.

**Acciones:**

1. Consumir la certificación del servidor desde FINAL y reconstruir/recuperar planes fiables, sin ejecutar contratos arbitrarios del cliente.
2. Mantener política de fallo cerrado para cobertura incompleta; convertir C05 de bloqueo global del fallback en autorización **selectiva**, solo para certificados.
3. Consolidar servicios de ejecución de lectura: evitar vías paralelas que puedan eludir el autorizador único.
4. Preservar identidad, sesión, caducidad, versión, bloqueo concurrente y permisos de acceso por ámbito.
5. Representar honestamente «no entendida», «requiere aclaración», «interpretada pero no certificada», «ejecutada» y «fallo HOST».
6. Verificar que tanto una propuesta QUERY determinista como una LLM sean auditadas por cobertura según capacidad y riesgo, no solo por `ok=True`.

**Archivos principales:** `final/contrato_respuesta.py`, `final/ejecutor_consultas.py`, `final/ejecucion_certificada.py`, `host/ejecutor_datos.py`, `final/formateador_respuesta.py`.

**Cierre:** no queda entrada pública de ejecución sin el punto común de autorización; casos H01–H13 cubiertos cuando sean certificables; si no, rechazo coherente sin ejecuciones incorrectas.

### ARC005 — Banco histórico y pruebas E2E permanentes

**Objetivo:** que ninguna modificación rompa silenciosamente una capacidad histórica y que ambas interfaces recorran el mismo camino.

**Acciones:**

1. Versionar las preguntas H01–H13 exactas, más mutaciones negativas; registrar expectativa de interpretación/cobertura y, si existe, respuesta de referencia de negocio.
2. Construir fixtures Django no sensibles y reproducibles con modelos de prueba que ejerciten filtros, OR, NOT, fechas, relaciones, selección de campos, orden y limitación.
3. Pruebas contra ambas URLs reales con Django Test Client y sesiones/usuarios adecuados, además de tests de servicio y PostgreSQL cuando sea necesario.
4. Verificar identidad de decisión/plan y efectos ORM, no igualdad superficial del HTML. Evitar conteos fijos de producción.
5. Incluir no regresión QUERY 15/15, FINAL 11/11, cobertura 8/8 y D06; incorporar batería de concurrencia a tests permanentes cuando proceda.
6. Marcar cuáles preguntas son «soportadas», cuáles «pendientes» y cuáles «requieren aclaración», evitando forzar `ok=True` por defecto.

**Cierre:** pruebas verifican el recorrido real sin divergencia principal/diagnóstico; preguntas cubiertas responden correctamente, las no cubiertas fallan de forma segura y comprensible.

### ARC006 — Portabilidad real entre Django anfitriones

**Objetivo:** validar en STIHL (o segundo anfitrión equivalente) que el núcleo no depende de Condocdat.

**Acciones:**

1. Documentar instalación de app, settings, rutas, migraciones, políticas y dependencias.
2. Descubrir modelos/relaciones/valores permitidos del nuevo anfitrión usando APIs Django.
3. Añadir, si hace falta, sinónimos y reglas de negocio **declarativos** específicos del anfitrión, nunca `if modelo == "rdi.RDIRecord"` en código portable.
4. Verificar consultas certificadas de conteo, listado y filtros (y nuevas capacidades solo si ARC003/004 las habilitaron).
5. Verificar igual tratamiento de permisos y decisiones de index/diagnóstico/API.
6. Reportar cada modificación requerida al núcleo: una adaptación específica no justificada es fallo de portabilidad.

**Cierre:** uso funcional con segundo anfitrión sin ramas Condocdat/STIHL incrustadas en el núcleo; evidencia automatizada y documentación de despliegue.

---

## 9. Orden de implementación y criterios de dirección

1. **ARC001 primero**, con inventario de rutas y pruebas HTTP de equivalencia. No ampliar la IA antes de asegurar la puerta canónica.
2. **ARC002**: contrato estable antes de conectar nuevas autorizaciones.
3. **ARC003**: certificación verificable y negativa/positiva delimitada.
4. **ARC004**: autorización real única, sin desbloquear indiscriminadamente Qwen.
5. **ARC005**: pruebas E2E crecientes desde ARC001 y cierre formal después de ARC004.
6. **ARC006**: portabilidad como criterio final de independencia.

Hitos transversales: cada spec requiere diagnóstico de impacto, cambios mínimos, rollback Git, pruebas positivas y negativas, pruebas desde interfaces, documentación de decisiones y checkpoint de aceptación. **No crear otra serie indefinida de instaladores sueltos y parches sin integración**.

---

## 10. Próxima tarea concreta al abrir nuevo chat

**Comenzar ARC001-A: inventario de entradas y recorrido real de la versión actual.**

Solicitar/inspeccionar (solo si no están disponibles en los adjuntos o repo):

- `ia_local/urls.py`
- `ia_local/views.py`
- `ia_local/views_desambiguacion.py` si interviene
- `ia_local/templates/ia_local/index.html`
- `ia_local/templates/ia_local/diagnostico.html`
- `ia_local/services/bridge/entrada_principal.py`
- `ia_local/services/bridge/orquestador_principal.py`
- `ia_local/services/final/orquestador_consultas.py`
- `ia_local/services/final/contrato_respuesta.py`
- `ia_local/services/final/ejecutor_consultas.py`
- `ia_local/services/final/formateador_respuesta.py`
- `ia_local/services/host/` router/ejecutor pertinente.

**Entregable ARC001-A:** mapa verificable de URLs → vistas → servicios → autorización → ejecutor → ORM para principal, diagnóstico y API; firma exacta de cada servicio, dependencias de sesión/usuario, rutas alternativas, y propuesta de una entrada canónica sin tocar Qwen ni los motores QUERY.

**Test mínimo inicial de ARC001:** ejecutar la misma pregunta `cuantas rdi estan abiertas` por las dos entradas con mismo contexto de permisos y registrar en qué capa divergen; después repetir `lista los ultmos 5 correos enviados`. Sin ejecutar modificaciones de datos de negocio.

**No hacer de entrada:** un `git restore` general, un `git add .`, quitar C05, enlazar directamente Qwen con el ORM, definir reglas específicas de RDI/Correo en código portable, ni declarar «todo aprobado» por tests unitarios existentes.

---

## 11. Comandos útiles y estado de Git

En el entorno correcto, desde raíz Condocdat con virtualenv:

```bash
git status --short
git log -1 --oneline
git diff --cached --check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations ia_local
python manage.py ia_query_regression
python manage.py ia_final_close
python manage.py test ia_local.tests.test_llm008_cobertura ia_local.tests.test_llm008_verificador
```

**Importante:** la migración 0009 está aplicada en el entorno del usuario, pero una instalación en nuevo anfitrión requerirá sus migraciones; no tocar producción sin respaldo. Los datos de negocio y dumps de Condocdat no deben entrar al repositorio por accidente. Se borraron varios archivos temporales `.bak`, instaladores y `Zone.Identifier`; no usar esos instaladores como fuente canónica si ya se han eliminado.

---

## 12. Registro de decisiones («ADRs» condensados)

**D-01.** `ia_local` es una app portable, desarrollada inicialmente en Condocdat; validar portabilidad después en STIHL. **Vigente.**

**D-02.** HOST descubre y valida reglas/metadatos; Qwen interpreta pero no ejecuta ORM por sí mismo. **Vigente.**

**D-03.** Diferenciar validez estructural de integridad semántica. **Vigente.**

**D-04.** Barrera C05 instalada por ejemplos reales de planes LLM incompletos. No revertir globalmente. **Vigente, con integración selectiva pendiente.**

**D-05.** D06-C1–C4 prueban conteo simple seguro, sin filtros, con expediente; no equivale a certificación general ni a integración HTTP. **Hecho/parcial.**

**D-06.** No reconstruir BRIDGE/QUERY/LLM desde cero ni volver totalmente a la versión anterior. **Vigente.**

**D-07.** Entradas de `/ia/index/` y `/ia/diagnostico/` deben compartir exactamente interpretación y autorización; diferenciarlas solo en presentación/trazabilidad. **Decidido, pendiente ARC001.**

**D-08.** Contrato semántico común con cobertura demostrable y procedencia de requisitos. **Decidido, pendiente ARC002/003.**

**D-09.** FINAL como autorización y despacho unificados; sin rutas paralelas que ejecuten con política propia. **Decidido, pendiente ARC004.**

**D-10.** H01–H13 + negativas como banco histórico; no todas fueron éxitos previamente, diferenciar resultados. **Decidido, pendiente ARC005.**

**D-11.** Segundo anfitrión valida ausencia de dependencias Condocdat en núcleo. **Decidido, pendiente ARC006.**

**D-12.** Crear checkpoint Git limpio antes de la refactorización; no consta confirmación final de commit/push. **Pendiente de verificar.**

---

## 13. Criterio final de éxito del proyecto

Una pregunta natural, con sus condiciones completas, debe:

1. Entrar por el **mismo motor** desde index, diagnóstico y API.
2. Ser interpretada mediante capacidades de HOST/BRIDGE/QUERY/Qwen sin depender de nombres codificados del anfitrión.
3. Conservar intención, entidad, filtros, lógica, relaciones, tiempos, orden, límite y campos de presentación relevantes.
4. Recibir una **certificación auténtica** de equivalencia semántica y autorización, o una denegación/aclaración fundada.
5. Ejecutarse **solo** por el ejecutor HOST autorizado sobre el ORM correcto.
6. Devolver una respuesta fiel y consistente, más trazabilidad cuando se solicita diagnóstico.
7. Pasar el banco histórico y las pruebas de seguridad sin retrocesos.
8. Repetirse en un segundo proyecto Django sin modificar el núcleo para entender su negocio.

**Frase rectora:** «No necesitamos reconstruir `ia_local`; necesitamos conciliar la capacidad funcional anterior con las garantías actuales mediante un circuito único, portable y verificable».

---

## 14. Texto breve para pegar al iniciar el próximo chat

> Estoy continuando `ia_local`, una app Django portable con HOST, BRIDGE, QUERY, FINAL y Qwen/Ollama. Adjunto el dosier maestro fechado 2026-10-23 y, si están disponibles, los ZIP `ia_local-anterior.zip` y `ia_local-actual.zip`. Lee el dosier completo; se aprobaron las especificaciones ARC001–ARC006 pero todavía **no se implementaron**. Se comprobaron 15/15 QUERY, 11/11 FINAL, 8/8 cobertura y D06-C4 10/10 de conteo simple. La barrera C05 bloquea fallback LLM sin certificación; no la elimines globalmente. Hay divergencia de entradas visuales y la ruta certificada está desconectada de FINAL. Quiero comenzar **ARC001-A** con un inventario verificable de URLs/vistas y el recorrido común de `/ia/index/` y `/ia/diagnostico/`, preservando código existente y evitando lógica específica de Condocdat. Las preguntas H01–H13 constituyen nuestra batería histórica. Confirma Git antes de modificar y dame un plan de intervención pequeño, comprobable y sin rutas paralelas.

*Fin del documento. Este archivo es un registro de decisiones y evidencia, no una afirmación de que todas las specs estén ya implementadas.*

---

## ACTUALIZACION ARC001 — IMPLEMENTACION VALIDADA

Fecha de referencia: 23 de octubre de 2026.

### Objetivo alcanzado

Se estableció una infraestructura de entrada canónica,
preparación HOST y auditoría semántica preventiva.

Las principales entradas HTTP fueron orientadas hacia
el procesamiento FINAL existente, eliminando la llamada
HOST directa desde la vista principal `/ia/`.

### Componentes incorporados

- ARC001-B01: contrato de entrada canónica.
- ARC001-B02: preparador de consultas HOST.
- ARC001-B03: integración del preparador.
- ARC001-B04: prueba real de interpretación mediante Qwen.
- ARC001-C01: detección de pérdida semántica.
- ARC001-C02: auditoría preventiva reutilizable.
- ARC001-C03: integración de auditoría en entrada canónica.
- ARC001-C04-A: protección staff en aclaraciones.
- ARC001-C04-B: adaptación HTML del resultado FINAL.
- ARC001-C04-C: regresiones de vistas y aclaraciones.
- ARC001-D: suite general de ia_local validada.

### Archivos principales

- ia_local/services/entrada_canonica.py
- ia_local/services/host/preparador_consulta_datos.py
- ia_local/services/llm/auditor_preparacion.py
- ia_local/services/final/adaptador_html_arc001.py
- ia_local/views.py
- ia_local/views_desambiguacion.py
- ia_local/tests/test_arc001_*.py

### Validaciones realizadas

- 44 pruebas específicas ARC001 aprobadas.
- 52 pruebas generales de ia_local aprobadas.
- Django system check sin errores.
- git diff --check sin observaciones.
- Prueba real del preparador con Qwen y catálogo HOST.

### Caso SEM-NEG-001

Pregunta A:
¿Cuántas RDI de civil están abiertas?

Plan observado:
- Modelo: rdi.RDIRecord
- Operación: contar
- status = ABIERTA
- discipline contiene civil

Pregunta B:
¿Hay alguna RDI de civil que no esté cerrada?

Plan incorrecto observado:
- Modelo: rdi.RDIRecord
- Operación: contar
- status = ABIERTA
- discipline contiene civil

Problema:
La pregunta B expresa negación de estado cerrado,
pero Qwen produjo una condición afirmativa de abierto.

No debe asumirse que no cerrado equivale a abierto
sin evidencia válida del dominio.

El auditor preventivo detectó la ausencia de negación
y mantuvo bloqueada la ejecución.

### Decisiones arquitectónicas

1. Conservar HOST, BRIDGE, QUERY, LLM y FINAL.
2. Evitar crear intérpretes paralelos.
3. Mantener C05 hasta disponer de certificación integral.
4. Diferenciar preparación, auditoría, certificación,
   autorización y ejecución.
5. Ningún plan preparado constituye autorización.
6. La entrada canónica todavía no ejecuta consultas.
7. Las vistas actuales comparten FINAL en los recorridos
   auditados, pero la incorporación definitiva de la
   entrada canónica a la ejecución sigue pendiente.
8. Las aclaraciones deben conservar identidad, sesión,
   token, vencimiento y controles de acceso.
9. Los modelos y reglas de Condocdat no deben codificarse
   específicamente dentro del núcleo portable ia_local.

### Limitaciones conocidas

- La prueba real de Qwen confirmó un caso concreto.
- Las pruebas HTTP utilizaron principalmente simulaciones.
- No se ha demostrado paridad extremo a extremo con
  middleware, usuarios y sesiones reales.
- Los permisos de negocio y el expediente D06 todavía
  no están integrados en la entrada ejecutable común.
- El auditor preventivo no certifica cobertura integral.
- La suite de Django no garantiza que todos los scripts
  históricos independientes hayan sido ejecutados.
- La función HOST histórica permanece disponible para
  compatibilidad; revisar cualquier consumidor futuro.

### Estado de las siguientes fases

ARC002: contrato semántico universal — pendiente.
ARC003: certificación semántica integral — pendiente.
ARC004: autorización y ejecución FINAL única — pendiente.
ARC005: regresión histórica extremo a extremo — pendiente.
ARC006: portabilidad a segundo proyecto Django — pendiente.

### Regla de continuidad

No autorizar consultas porque Qwen devuelva un plan
estructuralmente válido o una lista vacía de condiciones
no resueltas.

Toda condición original debe conservarse y verificarse
antes de ejecutar el ORM.

### Próximo punto de trabajo

Comenzar ARC002-A: inventario y formalización del
contrato semántico universal, reutilizando los componentes
de extracción, consolidación, cobertura y trazabilidad
ya existentes.

## ARC002 — AVANCE B01 A B03-B02

Fecha: 23 de octubre de 2026.

### Validación
- Suite general ia_local: 76/76 pruebas aprobadas.
- Django check: sin errores.
- git diff --check: sin observaciones.

### ARC002-B01
- Las restricciones vacías no demuestran integridad semántica.
- Se introduce revisión pendiente en la consolidación.
- No se modifica la ejecución funcional.

### ARC002-B02
- Se reutilizan los identificadores de trazabilidad existentes.
- Se introduce diagnóstico estructural de integridad.
- La colección no queda certificada automáticamente.

### ARC002-B03-A
- Se detectan señales de negación textual.
- La presencia de filtros no certifica su representación.

### ARC002-B03-B01
- Se conservan marcadores negativos, posiciones originales
  y fragmentos contextuales.
- El contexto próximo no equivale al alcance lógico.

### ARC002-B03-B02
- Las evidencias negativas se incorporan al diagnóstico
  de cobertura semántica.
- Se conservan los códigos y claves históricos.
- Ante fallos de localización se registra un pendiente.

### Limitaciones y seguridad
- No existe todavía certificación del alcance de NOT.
- No hay prueba de integridad semántica completa.
- Los identificadores estructurales no demuestran fidelidad.
- No se ha implementado autorización nueva de ejecución.
- HOST, FINAL y C05 permanecen sin intervención directa
  durante ARC002-B01 a B03-B02.

### Próximos pasos
- ARC002-B03-C: asociación verificable entre evidencias
  textuales e identificadores de requisitos.
- ARC002-C: estructura universal AND/OR/NOT.
- Mantener SEM-NEG-001 como regresión obligatoria.
