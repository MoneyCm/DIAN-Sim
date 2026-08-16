# Despliegue seguro de las Fases 1, 2 y 3

Este procedimiento instala, en orden, el alcance canónico OPEC, el corpus
reconciliado 236769, la evidencia pedagógica y las políticas versionadas de
simulacro. Las migraciones son aditivas y funcionan en *dry-run* por defecto;
ningún comando escribe sin `--apply`.

No ejecutes este procedimiento directamente por primera vez en producción.
Ensáyalo contra una copia SQLite restaurada o una rama/base temporal restaurada
de PostgreSQL/Neon. Consulta también `docs/OPERACION_SEGURA.md`.

## 0. Condiciones de entrada y recuperación probada

1. Congela despliegues y tareas que escriban preguntas, revisiones o intentos.
2. Registra la versión de código, responsable, fecha UTC y base objetivo sin
   copiar credenciales.
3. Crea un respaldo verificable y ensaya su restauración en un destino nuevo.
4. Conserva la base/rama anterior durante toda la ventana de observación.

Para SQLite:

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py backups\pre_fases_1_3.db --source dian_sim.db
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py verify backups\pre_fases_1_3.db
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py restore backups\pre_fases_1_3.db tmp\ensayo_restore.db
```

Los dos últimos comandos deben informar `"ok": true`. La copia, su
`*.manifest.json` y el recibo `*.restore.json` forman la evidencia de
recuperación. Ninguno se sobrescribe automáticamente.

Para PostgreSQL/Neon, crea un punto de recuperación/rama desde el proveedor y
un `pg_dump --format=custom` cuando esté disponible. Comprueba el SHA-256,
ejecuta `pg_restore --list` y restaura el volcado en una rama o base **nueva y
vacía** con `pg_restore --exit-on-error`. Ejecuta allí toda esta secuencia antes
de tocar producción. No uses `--clean` en producción ni pegues `DATABASE_URL`
en tickets o logs.

## 1. Preparar secretos y proceso

En producción configura mediante Streamlit Secrets o variables protegidas:

```text
DIAN_SIM_ENV=production
REQUIRE_DATABASE_URL=true
DATABASE_URL=<conexión PostgreSQL/Neon>
DIAN_SIM_FERNET_KEY=<clave Fernet estable>
AUTO_MIGRATE_SCHEMA=false
```

`DIAN_SIM_FERNET_KEY` debe conservarse entre despliegues. Cambiarla sin un plan
de rotación hace ilegibles las claves de proveedores ya cifradas. No almacenes
ninguno de estos valores en Git.

Ejecuta los comandos desde una terminal confiable con `DATABASE_URL` cargada en
el entorno, sin imprimirla. Para un ensayo SQLite reemplaza esa variable por la
URL de `tmp\ensayo_restore.db`.

## 2. Fase 1: identidad y alcance OPEC

Primero ejecuta el preflight sin `--apply`:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase1_opec_scope.py
```

El JSON debe identificar `DIAN-2676` y no reportar `conflicting_case_ids`,
`question_competition_conflicts` ni alcances inesperados. Hay dos rutas:

- si ya muestra casos y preguntas demostrados, aplica Fase 1 con el comando
  siguiente;
- si muestra cero demostrados porque el destino aún no contiene los UUID del
  snapshot curado, **no apliques Fase 1 todavía**: conserva el preflight y pasa
  a la reconciliación de la sección 3. El reconciliador puede crear las tablas
  Fase 1 y los alcances en la misma transacción que importa las candidatas.

Con el respaldo y el ensayo de restauración confirmados, la primera ruta usa:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase1_opec_scope.py --apply
.\.venv\Scripts\python.exe scripts\migrations\phase1_opec_scope.py
```

La segunda ejecución es la comprobación idempotente: no debe proponer
duplicados ni revelar nuevos conflictos.

## 3. Reconciliar el snapshot OPEC 236769

Antes de importar, crea una copia verificable del snapshot y úsala como fuente:

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py backups\opec236769_ingesta.db --source dian_sim_opec236769.db
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py verify backups\opec236769_ingesta.db
```

El reconciliador nunca hereda el destino remoto de manera implícita. Para
SQLite indica una URL local explícita. Para Neon/PostgreSQL, usa la variable
protegida en `--destination-url` y evita registrar el comando expandido:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\reconcile_opec236769_snapshot.py --source backups\opec236769_ingesta.db --destination-url $env:DATABASE_URL
```

El preflight debe informar exactamente 48 casos y 144 preguntas en la fuente,
`safe_to_apply: true` y `conflicts: []`. El material importado sigue siendo
candidato no verificado; reconciliar no equivale a aprobarlo ni habilitarlo
para medición. Solo entonces:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\reconcile_opec236769_snapshot.py --source backups\opec236769_ingesta.db --destination-url $env:DATABASE_URL --apply
.\.venv\Scripts\python.exe scripts\migrations\reconcile_opec236769_snapshot.py --source backups\opec236769_ingesta.db --destination-url $env:DATABASE_URL
```

En la última salida, `cases_to_create` y `questions_to_create` deben ser cero,
sin conflictos. Si la Fase 1 inicial se negó únicamente porque el destino no
tenía todavía el corpus, el reconciliador habrá creado las tablas aditivas y el
alcance durante su importación. En ese caso vuelve a ejecutar el preflight y el
`--apply` idempotente de Fase 1 antes de seguir: ahora debe reconocer exactamente
los 48 casos y 144 preguntas, sin conflictos ni nuevos alcances.

## 4. Fase 2: evidencia pedagógica y plan de estudio

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase2_learning_evidence.py
```

Exige `safe_to_apply: true` y `missing_required_tables: []`. Revisa la lista
exacta `tables_to_create`; si incluye algo distinto de las tablas aditivas de
Fase 2, detén el cambio. Después:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase2_learning_evidence.py --apply
.\.venv\Scripts\python.exe scripts\migrations\phase2_learning_evidence.py
```

La verificación idempotente debe terminar con `tables_to_create: []`.

## 5. Fase 3: política versionada de simulacro

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase3_simulation_policy.py
```

Exige `safe_to_apply: true`, `missing_required_tables: []` e
`incompatible_tables: []`. Luego:

```powershell
.\.venv\Scripts\python.exe scripts\migrations\phase3_simulation_policy.py --apply
.\.venv\Scripts\python.exe scripts\migrations\phase3_simulation_policy.py
```

La última salida debe mostrar `tables_to_create: []` y ninguna tabla
incompatible. Crear la tabla no inventa conteos, duración ni una GOA oficial;
esas decisiones se cargan como versiones explícitas desde administración.

## 6. Verificación antes de publicar

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Comprueba manualmente con dos usuarios/OPEC diferentes:

1. `Mis OPEC` activa el cargo correcto.
2. Banco, mapa, tutor, práctica, repasos y resultados muestran solo ese cargo.
3. Cambiar de OPEC invalida una sesión anterior en vez de mezclar resultados.
4. Las preguntas sin fuente precisa, vigencia y revisión individual no aparecen
   en práctica activa ni en medición.
5. `measurement`, `anchor` y `reserved` no aparecen en práctica cotidiana;
   `reserved` nunca se expone al aspirante.
6. Una práctica interrumpida se reanuda con el mismo OPEC, versión de política,
   respuestas, confianza y marcadas para revisión.
7. Una medición conserva sus reglas al finalizar y no usa retroalimentación ni
   ayudas durante el intento.

En Neon/PostgreSQL repite estas comprobaciones primero en la rama restaurada.
Publica el código solo después de aprobarlas y mantén observación de errores,
latencia, autenticación y escrituras durante la ventana acordada.

## 7. Reversión sin borrar tablas

No borres tablas ni ejecutes correcciones manuales bajo presión. Detén nuevas
escrituras y conserva evidencia de la incidencia.

- En Neon/PostgreSQL, cambia `DATABASE_URL` a la rama/base restaurada y ya
  validada, despliega la versión anterior y confirma autenticación y conteos.
- En SQLite, restaura hacia un archivo nuevo con el comando documentado; valida
  hash e integridad y promuévelo únicamente con la aplicación detenida.

Las tablas son aditivas, pero eso no convierte un *downgrade* de datos en
seguro. Conserva el destino fallido para análisis y no retires el respaldo
anterior hasta cerrar formalmente la recuperación.
