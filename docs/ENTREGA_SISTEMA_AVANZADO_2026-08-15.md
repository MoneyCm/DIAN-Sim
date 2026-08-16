# Informe verificable de entrega — sistema avanzado OPEC 236769

**Fecha de corte:** 15 de agosto de 2026
**Proceso:** DIAN 2676
**OPEC objetivo:** 236769
**Empleo:** Gestor III, código 303, grado 03
**Ficha MERF:** AT-FL-3006
**Estado de la entrega:** **implementación avanzada disponible en el repositorio; migración y validación productiva pendientes**

## 1. Conclusión ejecutiva

El proyecto dejó de ser únicamente un simulador con preguntas sueltas y ahora dispone de una arquitectura orientada a una OPEC exacta: fuentes y revisiones versionadas, particiones de banco, evidencia de aprendizaje, diagnóstico por las nueve funciones, dificultad editorial de 1 a 10, cuaderno de errores, modos de práctica, reanudación, simulacros internos con política versionada, plan de estudio, biblioteca, tutor, analítica de preparación y controles de seguridad.

El resultado **no permite afirmar todavía que la preparación de OPEC 236769 esté terminada ni que garantice ganar el concurso**. La meta de 85/100 es un umbral interno exigente para orientar el entrenamiento; no es una predicción ni un puntaje oficial. El mínimo funcional oficial publicado es 70/100, pero el resultado real depende de la prueba CNSC, de la modalidad de la vacante, de las ponderaciones aplicables y del desempeño del aspirante.

Al corte:

- la implementación de las Fases 1 a 5 está presente en código, con distintos niveles de cierre que se detallan abajo;
- ninguna migración fue aplicada a la base de datos real o remota;
- los *dry-runs* locales y el pipeline completo sobre una base temporal fueron exitosos;
- la suite completa de la rama de publicación reportó **593 pruebas superadas**, sin fallos y con la caché de `pytest` deshabilitada;
- el corpus cerrado de 48 casos y 144 preguntas fue reconocido e importable como **candidatas no verificadas**, no como material habilitado;
- no se generó el banco meta de 2.200 ítems: la distribución 1.500 funcionales, 400 comportamentales y 300 de integridad es una meta editorial, no un banco existente ni una ponderación oficial;
- la validación manual en producción, multiusuario, OAuth y móvil sigue pendiente.

## 2. Qué se encontró

### 2.1 Estado normativo y del proceso

La investigación oficial permitió comprobar lo siguiente:

- la ficha MERF AT-FL-3006 sustenta el propósito, los requisitos, las competencias y las nueve funciones del empleo;
- la metodología funcional disponible está construida como Prueba de Juicio Situacional (PJS): caso laboral, enunciado, tres opciones, una clave y hasta tres enunciados por caso;
- las pruebas comportamental y de integridad se describen como autorreporte Likert de cuatro opciones, sin clave de respuesta correcta;
- al 15 de agosto de 2026 no se localizó en el portal oficial una GOA de pruebas escritas específica de DIAN 2676, ni ejes e indicadores definitivos para OPEC 236769;
- tampoco estaban publicados la cantidad definitiva de ítems, la duración del cuadernillo ni la citación de aplicación;
- la modalidad particular de la vacante debe conservarse desde evidencia autenticada de SIMO antes de asignarle una tabla de ponderaciones.

Por ello, el sistema distingue entre dato oficial, decisión editorial provisional y dato no publicado. Los valores locales como 60 preguntas, 120 minutos o meta 85 no se presentan como parámetros CNSC.

### 2.2 Estado del banco heredado

El snapshot auditado contiene 48 casos y 144 preguntas funcionales con identificadores deterministas y cobertura declarada de F1 a F9. No obstante, cada ítem carece todavía de la verificación completa exigida por el nuevo contrato editorial: URL oficial precisa, localizador, fragmento probatorio suficiente, vigencia, fecha de consulta, revisión individual, explicación de distractores y control de duplicidad.

La decisión correcta fue conservarlos en `training` como candidatas no verificadas. No se promovieron automáticamente a `measurement`, `anchor` ni al banco activo. El banco objetivo de 2.200 preguntas quedó definido como arquitectura de crecimiento progresivo; **no se rellenó con contenido masivo de baja calidad**.

## 3. Estado por fases

| Fase | Alcance solicitado | Entrega verificable | Estado real al corte |
|---|---|---|---|
| 1 | OPEC exacta, investigación oficial, matriz F1-F9, aislamiento y banco curado | Matriz versionada, registro de fuentes, modelos de alcance OPEC, citas y revisiones; reconciliador conservador del snapshot | **Implementada en código; contenido y producción pendientes** |
| 2 | Motor adaptativo, diagnóstico, dominio, dificultad, errores y readiness 85 | Evidencia canónica por sesión/evento, diagnóstico balanceado, dificultad 1-10, cuaderno de errores, repetición espaciada y compuerta de preparación | **Implementada; requiere historial real suficiente** |
| 3 | Modos de práctica, simulacro realista, reanudación y administración editorial | Modos por función/tema/error/parcial/completo, selección por casos, política versionada, reanudación segura, particiones y revisión exigente | **Implementada; parámetros oficiales pendientes** |
| 4 | Plan, biblioteca, tutor, analítica y UX | Misión diaria explicable, biblioteca oficial/editorial diferenciada, tutor socrático, paneles de preparación y navegación simplificada | **Implementada; validación de uso real pendiente** |
| 5 | Seguridad, pruebas, migración, despliegue y recuperación | Secretos *fail-closed*, cargas seguras, límites IA, errores sanitizados, migraciones aditivas con *dry-run* y suite automatizada | **QA local avanzado; despliegue real no ejecutado** |

### 3.1 Fase 1 — evidencia, OPEC y banco

Se implementó una matriz exacta para OPEC 236769 con las nueve funciones en el orden del MERF, fuentes oficiales, vínculos temáticos, niveles cognitivos y metas editoriales. Los ejes derivados y los objetivos numéricos están rotulados como provisionales.

Módulos y evidencias principales:

- `data/opec_236769_matrix.json`: matriz versionada, estado de publicaciones, nueve funciones y 16 fuentes registradas;
- `core/opec_236769.py` y `core/preparation_matrix.py`: correspondencia de cobertura F1-F9 y lectura de la matriz;
- `core/source_evidence.py`: contrato de evidencia precisa por ítem;
- `core/question_review.py`, `core/question_quality.py` y `core/legacy_question_audit.py`: revisión estructural, editorial y de fuente;
- `core/exam_format.py`: separación PJS funcional y Likert sin clave;
- `db/models.py`: `OpecProfile`, alcances de preguntas/casos, documentos, citas y revisiones;
- `services/question_service.py`: aislamiento por concurso, OPEC y partición;
- `core/bank_partition.py`: `training`, `measurement`, `anchor` y `reserved`, con promoción explícita y auditable;
- `scripts/migrations/phase1_opec_scope.py`: migración aditiva, idempotente y en *dry-run* por defecto;
- `scripts/migrations/reconcile_opec236769_snapshot.py`: reconciliación de solo lectura por defecto; importa únicamente el inventario cerrado de 48/144 y lo deja como candidato no verificado.

La habilitación de una pregunta ahora exige más que una forma correcta o una recomendación de IA. Una auditoría automática puede ayudar a detectar problemas, pero no sustituye la evidencia jurídica individual ni promociona contenido por sí sola.

### 3.2 Fase 2 — aprendizaje medible y preparación

Se creó un modelo canónico de aprendizaje por usuario, concurso y OPEC. Conserva sesiones, eventos, estado temático, confianza, tiempo, errores y actividades del plan sin mezclar resultados de otras vacantes.

Módulos principales:

- `core/learning/evidence_service.py` y `core/learning/session_service.py`: registro transaccional de evidencia;
- `core/learning/difficulty.py`: dificultad editorial de 1 a 10;
- `core/diagnostic.py`: diagnóstico balanceado en las nueve funciones;
- `core/error_notebook.py`: diez categorías de error y superación mediante transferencia novedosa espaciada;
- `core/learning/review_policy.py`: política de repaso;
- `core/readiness_gate.py`: preparación interna prudente, separada del resultado oficial;
- `core/study_recommendations.py`: prioridad explicable por debilidad, vencimiento y cobertura;
- `scripts/migrations/phase2_learning_evidence.py`: tablas aditivas de sesiones, eventos, estados, errores, planes y actividades.

La compuerta de readiness no se activa con un único resultado. Requiere tres sesiones comparables recientes, completas, sin ayuda ni retroalimentación durante la medición, con la misma versión de banco/política, preguntas funcionales confiables, cobertura F1-F9 y sin repetición. La retención se informa aparte y los ítems Likert no se convierten en aciertos funcionales.

### 3.3 Fase 3 — entrenamiento y simulación

Se implementaron modos `recomendado`, por tema, competencia, función, errores, parcial, completo y máximo. La selección estricta conserva casos completos y evita usar la partición reservada. Los tamaños de parcial/completo provienen de una política versionada por OPEC, no de números dispersos en la interfaz.

Módulos principales:

- `core/practice_modes.py`: modos, límites de exposición y selección por casos;
- `core/simulation_policy.py` y `core/simulation_policy_store.py`: contrato inmutable y una sola versión activa;
- `scripts/migrations/phase3_simulation_policy.py`: tabla aditiva de políticas;
- `core/real_exam.py` y `app/pages/Simulacro_Real.py`: navegación, temporizador, cantidad exacta cuando se configura y modo interno sin ayudas;
- `core/study_resume.py`, `app/pages/1_Nuevo_Simulacro.py` y `app/pages/2_Ejecucion.py`: checkpoint y reanudación de prácticas; diagnóstico y medición no se reanudan;
- `app/pages/5_Banco_Preguntas.py`: cola editorial, evidencia, metadatos, explicaciones de distractores y control de duplicidad;
- `app/pages/8_Panel_Admin.py`: administración versionada de política de simulacro.

El estado reanudable conserva respuestas, confianza, razonamiento, tiempo efectivo, marcas para revisar y contexto exacto. El tiempo fuera de línea no se suma como tiempo de respuesta. Las políticas oficiales no se completan con supuestos: cantidad, duración y ejes continúan nulos hasta que exista una publicación verificable.

### 3.4 Fase 4 — experiencia de estudio

Se integraron superficies enfocadas en la decisión diaria del aspirante:

- `app/pages/6_Dashboard.py`: OPEC activa, misión de hoy, progreso prudente y reanudación rápida;
- `app/pages/11_Plan_Estudio.py`: fecha meta, disponibilidad, días, actividades y aplazamiento, siempre por OPEC;
- `core/study_library.py` y `app/pages/16_Biblioteca_Estudio.py`: núcleo oficial separado del corpus editorial relacionado;
- `core/learning/tutor.py`, `core/socratic_tutor.py` y `app/pages/13_Tutor_Adaptativo.py`: tutor socrático que solicita razonamiento, explica reglas y no inventa excepciones ni citas;
- `app/pages/10_Repaso_Especial.py`: cuaderno de errores y repaso vencido;
- `app/pages/12_Mapa_Estudio.py` y `app/pages/3_Resultados.py`: cobertura y evidencia de desempeño sin presentar un puntaje local como resultado oficial;
- `app/pages/14_Mis_OPEC.py` y navegación principal: selección explícita de la vacante y reducción de ruido para el usuario normal.

La utilidad final de estos módulos dependerá de disponer de suficientes preguntas verificadas y de recoger sesiones reales. Un tablero completo con datos insuficientes no constituye evidencia de preparación.

### 3.5 Fase 5 — operación, seguridad y QA

Controles relevantes implementados:

- `core/security_keys.py` y `db/session.py`: configuración productiva cerrada ante secretos o conexión inválidos;
- protección CORS/XSRF activada;
- `core/safe_uploads.py`: límites de tamaño y validación de tipo, contenido, páginas, cifrado, rutas y colisiones;
- `core/ai/usage_policy.py`: límites persistentes de llamadas, tokens y salida;
- mensajes de error sanitizados y telemetría sin exponer credenciales;
- autorización administrativa aplicada a acciones sensibles;
- procesamiento de biblioteca y enriquecimiento por lotes acotados;
- pruebas unitarias, de integración, migración, aislamiento OPEC, seguridad y contratos UI.

La ejecución completa de la rama de publicación reportó **593 pruebas superadas**, sin fallos y con la caché de `pytest` deshabilitada. Este número es evidencia de regresión automatizada, no una certificación productiva; debe complementarse con pruebas manuales reales en producción, OAuth, dispositivos móviles y concurrencia multiusuario.

## 4. Migraciones y estado de los datos

### 4.1 Lo que sí se verificó

- Los cuatro comandos son de inspección por defecto; solo escriben cuando reciben `--apply`.
- Los *dry-runs* locales fueron exitosos.
- Un pipeline temporal ejecutó creación/aplicación/verificación sobre una base desechable sin tocar la base real.
- La reconciliación valida que fuente y destino no sean el mismo archivo, exige exactamente 48 casos y 144 preguntas, detecta conflictos antes de escribir y mantiene `is_verified=False`.
- Las migraciones son aditivas y crean sus tablas con comprobación de existencia.

### 4.2 Lo que no se ejecutó

- No se modificó la base remota de Streamlit Cloud.
- No se aplicaron Fase 1, reconciliación, Fase 2 ni Fase 3 a una base productiva.
- No se promovieron las 144 preguntas a banco de medición.
- No se verificaron conteos posteriores a una migración real.

### 4.3 Comandos de preflight

Ejecutar siempre contra una URL explícita y después de respaldar. Los siguientes comandos **no escriben** porque omiten `--apply`:

```powershell
.venv\Scripts\python.exe scripts\migrations\phase1_opec_scope.py --database-url "<URL_DESTINO>"
.venv\Scripts\python.exe scripts\migrations\reconcile_opec236769_snapshot.py --source "<SNAPSHOT_48_144>" --destination-url "<URL_DESTINO>"
.venv\Scripts\python.exe scripts\migrations\phase2_learning_evidence.py --database-url "<URL_DESTINO>"
.venv\Scripts\python.exe scripts\migrations\phase3_simulation_policy.py --database-url "<URL_DESTINO>"
```

No debe añadirse `--apply` en producción hasta revisar el respaldo, la identidad de destino, el informe JSON de cada preflight y los conflictos. La reconciliación puede crear el esquema aditivo de Fase 1 e importar/asignar el snapshot en una transacción; por ello, el orden definitivo de escritura debe seguir el resultado del preflight y no una secuencia ciega.

## 5. Evidencia oficial registrada

La fuente canónica completa, con fecha de consulta, localizadores, vigencia y función de cada documento, está en `data/opec_236769_matrix.json`. Enlaces oficiales principales:

- [Acuerdo CNSC No. 21 de 2025](https://www.cnsc.gov.co/sites/default/files/2025-11/acuerdo-no-21-dian-2676-de-20251.pdf): reglas y pruebas del proceso; no determina por sí solo la modalidad de esta vacante.
- [Anexo del Proceso de Selección DIAN 2676](https://www.cnsc.gov.co/sites/default/files/2025-11/anexo_ps-dian-2676-de-2025.pdf): alcance general y publicación posterior de la GOA/citación.
- [Portal oficial DIAN 2676](https://www.cnsc.gov.co/convocatorias/dian-2676): canal que debe monitorearse para nuevas guías, avisos y resultados.
- [Especificaciones técnicas LP-004-2026](https://community.secop.gov.co/Public/Archive/RetrieveFile/Index?DocumentId=783745811&InCommunity=False&InPaymentGateway=False): metodología PJS/Likert disponible; no fija cantidad o duración del cuadernillo.
- [Documento SIMO asociado a OPEC 236769](https://simo.cnsc.gov.co/documents/get-document?contentType=application%2Fpdf&docId=559927710): ficha particular; puede exigir sesión y debe conservarse como evidencia autenticada.
- [Ficha MERF AT-FL-3006](https://www.dian.gov.co/dian/entidad/ManualdeFunciones/FT_TAH_1824_Gestor_III_AT_FL_3006.pdf): propósito, nueve funciones, requisitos y competencias.
- [Resolución DIAN 0067 de 2024](https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0067_2024.htm): adopción del MERF.
- [Resolución DIAN 0065 de 2024](https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0065_2024.htm) y [Diccionario de Competencias Comportamentales](https://www.dian.gov.co/dian/entidad/Documents/Diccionario-de-Competencias-Comportamentales-Res-065-2024.pdf).
- [Estatuto Tributario compilado](https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm), [Decreto 1625 de 2016](https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm), [Decreto 1165 de 2019](https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1165_2019.htm), [Resolución DIAN 0046 de 2019](https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0046_2019.htm), [Decreto-Ley 2245 de 2011](https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2245_2011.htm) y [Ley 1437 de 2011](https://normograma.dian.gov.co/dian/compilacion/docs/ley_1437_2011.htm): corpus que requiere contraste artículo por artículo.

Una URL general o el nombre de una norma no valida una pregunta. Cada ítem debe guardar artículo/apartado, fragmento, fecha de consulta, vigencia y correspondencia explícita con clave y distractores.

## 6. Riesgos y limitaciones abiertas

1. **Publicación oficial incompleta.** GOA, ejes definitivos, cantidad de ítems, duración y citación no estaban publicados al corte. Deben incorporarse como una nueva versión cuando aparezcan.
2. **Banco todavía provisional.** Los 48 casos/144 preguntas permanecen como candidatas. La meta 2.200 no fue generada y no debe llenarse automáticamente para alcanzar un contador.
3. **Revisión jurídica y psicométrica.** Los controles de software detectan estructura, fuentes incompletas, sesgos simples y duplicidad, pero no sustituyen la revisión sustantiva ni una calibración con datos reales.
4. **Producción sin migrar.** La base remota puede tener esquema y datos distintos a los auditados localmente. Cualquier escritura sin respaldo y preflight sería insegura.
5. **Validación multiusuario pendiente.** Falta comprobar en producción registro tradicional, Google OAuth, cuentas nuevas/antiguas, aislamiento entre usuarios, varios concursos, móvil, latencia y concurrencia.
6. **Recuperación no ensayada sobre producción.** Debe probarse restauración desde copia, no solo creación del respaldo.
7. **Dependencia del proveedor IA.** La auditoría externa puede fallar, devolver JSON inválido o sufrir cuota/latencia. El sistema debe conservar pendientes, no aprobar ni descartar por error técnico.
8. **Escala interna, no predicción.** Readiness 85 mide evidencia local comparable; no asegura selección, no reemplaza el mínimo oficial ni estima una posición en lista.
9. **Contenido comportamental/integridad heredado.** Cualquier material antiguo con A/B/C y clave debe mantenerse fuera de medición hasta migrarlo a Likert sin acierto/error.
10. **Operación de archivos e IA.** La extracción PDF sigue ocurriendo en el proceso web y algunos caminos heredados de IA requieren comprobar que utilicen el medidor central bajo carga concurrente.

## 7. Pasos manuales obligatorios antes de producción

1. Congelar una ventana de despliegue y registrar el commit exacto que se va a publicar.
2. Crear un respaldo verificable de la base remota, con fecha, tamaño, checksum y ubicación protegida.
3. Restaurar ese respaldo en un entorno temporal y comprobar que la recuperación funciona.
4. Ejecutar la suite final completa; registrar versión de Python, dependencias, total y duración.
5. Ejecutar los cuatro preflights contra la copia restaurada y revisar el JSON, especialmente conflictos, conteos y destino.
6. Aplicar las migraciones primero sobre la copia temporal; ejecutar pruebas de humo y verificar que los 48/144 estén en `training`, no activos.
7. Repetir respaldo inmediato y preflight sobre producción; solo entonces autorizar `--apply` de forma explícita.
8. Crear la primera política interna de simulacro para OPEC 236769 desde el panel, sin completar campos oficiales desconocidos.
9. Probar manualmente con al menos un administrador, un usuario existente y un usuario nuevo: registro, OAuth, Mis OPEC, cambio de OPEC, práctica, reanudación, resultados, plan, biblioteca y cierre de sesión.
10. Probar móvil y escritorio, reconexión, dos sesiones simultáneas y aislamiento de datos entre usuarios/OPEC.
11. Revisar una muestra editorial por cada función y dificultad antes de cualquier promoción masiva.
12. Monitorear el portal oficial DIAN 2676; al publicarse GOA/ejes/logística, crear una nueva versión de matriz, política y banco sin sobrescribir la evidencia histórica.

## 8. Criterios de aceptación pendientes

La entrega podrá declararse productiva para OPEC 236769 solo cuando se cumplan conjuntamente:

- migraciones aplicadas con respaldo restaurable y conteos conciliados;
- autenticación y aislamiento multiusuario verificados en la URL pública;
- cero preguntas no verificadas en las particiones `measurement` y `anchor`;
- cobertura mínima confiable F1-F9 y suficientes casos completos para los modos configurados;
- política activa coherente con las publicaciones oficiales disponibles;
- tres mediciones comparables que sustenten el readiness de cada usuario, sin presentar 85 como garantía;
- métricas, logs y límites IA operando sin exponer secretos ni errores internos;
- prueba de humo móvil/escritorio posterior al despliegue;
- procedimiento de rollback probado.

## 9. Evidencias de repositorio para auditoría

- Diagnóstico normativo y técnico inicial: `docs/FASE_1_OPEC_236769_2026-08-15.md`.
- Matriz canónica: `data/opec_236769_matrix.json`.
- Despliegue seguro inicial: `docs/DESPLIEGUE_FASE_1.md`.
- Modelos persistentes: `db/models.py`.
- Migraciones: `scripts/migrations/phase1_opec_scope.py`, `scripts/migrations/reconcile_opec236769_snapshot.py`, `scripts/migrations/phase2_learning_evidence.py` y `scripts/migrations/phase3_simulation_policy.py`.
- Pruebas: suites `tests/test_phase1_opec_scope_migration.py`, `tests/test_reconcile_opec236769_snapshot.py`, `tests/test_phase2_learning_evidence.py`, `tests/test_simulation_policy.py`, `tests/test_simulation_policy_store.py`, `tests/test_readiness_gate.py`, `tests/test_practice_modes.py`, `tests/test_study_resume.py`, `tests/test_bank_partition.py`, `tests/test_question_review.py`, `tests/test_question_quality.py`, `tests/test_safe_uploads.py` y `tests/test_ai_usage_policy.py`, entre otras.

## 10. Declaración final

La entrega establece una base técnica considerablemente más rigurosa y segura para estudiar OPEC 236769. Su mayor mejora no es aumentar el contador de preguntas, sino impedir que material sin procedencia, sin vigencia o sin revisión se confunda con preparación confiable. La siguiente etapa correcta es operacional: respaldar, migrar en un clon, revalidar, desplegar de forma controlada y construir gradualmente un banco verificado con evidencia oficial.

No existe base técnica ni jurídica para prometer que la aplicación hará ganar el concurso. Sí existe ahora una arquitectura para medir preparación de manera más honesta, orientar el estudio hacia F1-F9 y elevar progresivamente la calidad del entrenamiento conforme aparezcan publicaciones oficiales y evidencia de desempeño real.
