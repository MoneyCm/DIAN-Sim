# Operación segura de DIAN SIM

## Variables obligatorias en producción

Configura `DATABASE_URL` únicamente en Streamlit Secrets o variables protegidas.
Activa `REQUIRE_DATABASE_URL=true` para impedir el fallback accidental a SQLite.
Configura `DIAN_SIM_ENV=production` y una `DIAN_SIM_FERNET_KEY` Fernet estable;
la aplicación debe fallar al arrancar si falta alguno de los secretos obligatorios.
No guardes claves de Neon, LLM o cookies en archivos versionados.
Mantén `AUTO_SEED_OPEC_BANKS=false` en el servicio web. La carga de bancos es
una tarea administrativa versionada, no una acción del inicio de sesión.

## Rotación de Neon

1. Genera una contraseña nueva en Neon.
2. Actualiza `DATABASE_URL` en el proveedor de despliegue.
3. Comprueba el arranque y el inicio de sesión.
4. Revoca la contraseña anterior.
5. Elimina la credencial del historial Git mediante el procedimiento aprobado
   por el equipo (reescritura coordinada y posterior rotación de clones).

## Respaldo y recuperación local verificables

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py
```

El respaldo usa la API online de SQLite, por lo que incorpora transacciones
confirmadas que todavía estén en el archivo WAL. Se crea en `backups/` con un
nombre único y un manifiesto adyacente `*.manifest.json`. El comando se niega a
sobrescribir tanto la copia como el manifiesto, ejecuta
`PRAGMA integrity_check` y registra tamaño, versión de usuario y SHA-256. El
manifiesto no contiene la ruta del origen, `DATABASE_URL` ni credenciales.

Para indicar otro origen o destino:

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py backups\antes_fase1.db --source dian_sim.db
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py verify backups\antes_fase1.db
```

No continúes con una migración si `verify` no termina con `"ok": true`. Conserva
juntos el `.db` y su `.manifest.json` en almacenamiento distinto al servidor de
la aplicación.

La recuperación deliberadamente no reemplaza la base activa. Primero crea y
valida una base nueva, además de un recibo `*.restore.json`:

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py restore backups\antes_fase1.db tmp\recuperada.db
```

Ejecuta la aplicación o las verificaciones de esquema contra
`tmp\recuperada.db`. Solo con la aplicación detenida y la validación aprobada
se puede promover esa copia mediante un cambio de nombre controlado. Conserva
la base anterior hasta cerrar formalmente la incidencia.

## PostgreSQL/Neon: respaldo y ensayo de recuperación

Antes de modificar el esquema remoto, crea un punto de recuperación o una rama
de respaldo desde el panel de Neon y, además, un volcado lógico cuando el plan y
los permisos lo permitan. Usa un cliente `pg_dump` compatible con la versión
del servidor y no imprimas ni guardes la URL en logs o en el repositorio:

```powershell
$dump = "backups\dian_sim_predeploy_$(Get-Date -Format yyyyMMdd_HHmmss).dump"
pg_dump --format=custom --no-owner --no-privileges --file $dump $env:DATABASE_URL
Get-FileHash -Algorithm SHA256 $dump
pg_restore --list $dump
```

El hash debe registrarse en el cambio operativo sin copiar la credencial. Un
listado exitoso de `pg_restore --list` valida el contenedor, pero no sustituye
un ensayo de restauración. Restaura primero en una base o rama nueva y vacía:

```powershell
$env:DIAN_SIM_RESTORE_URL = "<URL protegida de una rama temporal vacía>"
pg_restore --exit-on-error --no-owner --no-privileges --dbname $env:DIAN_SIM_RESTORE_URL $dump
```

Contra esa rama temporal ejecuta los preflight de las migraciones, la suite de
pruebas y comprobaciones de conteos/aislamiento OPEC. No uses `--clean` contra
producción. La recuperación se completa cambiando `DATABASE_URL` a la rama
restaurada solo después de aprobar esas verificaciones; conserva la rama
anterior hasta confirmar arranque, autenticación y lecturas/escrituras.

## Verificación previa a despliegue

```powershell
$env:REQUIRE_DATABASE_URL = "true"
.\.venv\Scripts\python.exe -m pytest -q
```
