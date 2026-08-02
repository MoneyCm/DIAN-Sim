# Operación segura de DIAN SIM

## Variables obligatorias en producción

Configura `DATABASE_URL` únicamente en Streamlit Secrets o variables protegidas.
Activa `REQUIRE_DATABASE_URL=true` para impedir el fallback accidental a SQLite.
No guardes claves de Neon, LLM o cookies en archivos versionados.

## Rotación de Neon

1. Genera una contraseña nueva en Neon.
2. Actualiza `DATABASE_URL` en el proveedor de despliegue.
3. Comprueba el arranque y el inicio de sesión.
4. Revoca la contraseña anterior.
5. Elimina la credencial del historial Git mediante el procedimiento aprobado
   por el equipo (reescritura coordinada y posterior rotación de clones).

## Respaldo local

```powershell
.\.venv\Scripts\python.exe scripts\backup\backup_sqlite.py
```

El respaldo se crea en `backups/` con fecha y hora. Antes de una actualización,
crea una copia y verifica que el archivo pueda abrirse con SQLite.

## Verificación previa a despliegue

```powershell
$env:REQUIRE_DATABASE_URL = "true"
.\.venv\Scripts\python.exe -m pytest -q
```

