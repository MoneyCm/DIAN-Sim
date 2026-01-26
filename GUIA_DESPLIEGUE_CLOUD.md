# 🚀 Guía de Despliegue en Streamlit Cloud

Para que puedas acceder a tu simulador desde cualquier lugar (incluyendo tu móvil fuera de la red local), sigue estos pasos:

## 1. Preparar el Repositorio
1. Asegúrate de que tu código esté en **GitHub** (repositorio privado o público).
2. El archivo `requirements.txt` ya incluye todas las dependencias necesarias.

## 2. Configurar en Streamlit Cloud
1. Ve a [share.streamlit.io](https://share.streamlit.io/) e inicia sesión con tu cuenta de GitHub.
2. Haz clic en **"New app"**.
3. Selecciona tu repositorio y la rama principal.
4. En **"Main file path"**, escribe: `app/🏠_Inicio.py`.

## 3. Configurar Secretos (CRÍTICO) 🔐
Antes de desplegar, haz clic en **"Advanced settings..."** > **"Secrets"** y pega lo siguiente, reemplazando con tus valores:

```toml
DATABASE_URL = "postgres://your_supabase_url_here"
DEFAULT_PROVIDER = "gemini" # o groq, openai
GEMINI_API_KEY = "tu_clave_aqui"
GROQ_API_KEY = "tu_clave_aqui"
OPENAI_API_KEY = "tu_clave_aqui"
```

> [!IMPORTANT]
> Usa la URL de conexión de Supabase (PostgreSQL) para que los datos persistan en la nube.

## 4. Acceso Móvil
Una vez desplegada, obtendrás una URL tipo `https://dian-sim.streamlit.app`.
- Abre esa URL en tu celular.
- El diseño ya está optimizado para pantallas pequeñas.
- El cronómetro flotará en la parte superior derecha para no estorbar.

## 5. Ventajas de estar en la Nube
- **Sincronización**: Estudia en el PC y revisa resultados en el móvil.
- **Tutor IA**: Funciona nativamente usando los secretos que configuraste.
- **Gráficos**: El Dashboard se actualizará en tiempo real con cada intento.
