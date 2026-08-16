# Guía de despliegue controlado en Streamlit Cloud

Antes de publicar, crea un respaldo restaurable y ensaya las migraciones en una
rama o base temporal de Neon. Sigue el orden exacto descrito en
[`docs/DESPLIEGUE_FASE_1.md`](docs/DESPLIEGUE_FASE_1.md) y la recuperación de
[`docs/OPERACION_SEGURA.md`](docs/OPERACION_SEGURA.md).

## 1. Preparar el Repositorio
1. Asegúrate de que tu código esté en **GitHub** (repositorio privado o público).
2. El archivo `requirements.txt` ya incluye todas las dependencias necesarias.

## 2. Configurar en Streamlit Cloud
1. Ve a [share.streamlit.io](https://share.streamlit.io/) e inicia sesión con tu cuenta de GitHub.
2. Haz clic en **"New app"**.
3. Selecciona tu repositorio y la rama principal.
4. En **"Main file path"**, escribe: `app/app.py`.

No uses `app/🏠_Inicio.py`: ese archivo no pertenece a la aplicación actual.

## 3. Configurar Secretos (CRÍTICO) 🔐
Antes de desplegar, haz clic en **"Advanced settings..."** > **"Secrets"** y pega lo siguiente, reemplazando con tus valores:

```toml
DIAN_SIM_ENV = "production"
REQUIRE_DATABASE_URL = true
DATABASE_URL = "<URL PostgreSQL/Neon vigente>"
DIAN_SIM_FERNET_KEY = "<clave Fernet estable>"
AUTO_MIGRATE_SCHEMA = false
AUTO_SEED_OPEC_BANKS = false
```

> [!IMPORTANT]
> Usa una URL PostgreSQL/Neon vigente. Conserva `DIAN_SIM_FERNET_KEY` entre
> despliegues y agrega únicamente las claves de los proveedores IA utilizados.
> Nunca guardes estos valores en Git.

Para Google OAuth, el callback registrado debe ser exactamente
`https://dian-sim-master.streamlit.app/oauth2callback`.

## 4. Orden seguro de publicación

1. Congela escrituras durante la ventana de mantenimiento.
2. Crea y verifica un respaldo; restaura una rama temporal.
3. Ejecuta allí los *dry-runs* y las Fases 1, 2 y 3.
4. Valida dos usuarios con OPEC distintas, OAuth, móvil y reanudación.
5. Aplica las migraciones aditivas en producción.
6. Publica el commit aprobado y observa errores, latencia y escrituras.

No actives `AUTO_MIGRATE_SCHEMA` como sustituto de este procedimiento.

## 5. Acceso móvil
Una vez desplegada, obtendrás una URL tipo `https://dian-sim.streamlit.app`.
- Abre esa URL en tu celular.
- El diseño ya está optimizado para pantallas pequeñas.
- El cronómetro flotará en la parte superior derecha para no estorbar.

## 6. Ventajas de estar en la nube
- **Sincronización**: Estudia en el PC y revisa resultados en el móvil.
- **Tutor IA**: Funciona nativamente usando los secretos que configuraste.
- **Gráficos**: El Dashboard se actualizará en tiempo real con cada intento.
