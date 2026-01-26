# DianSim: Simulador de Concurso DIAN 🇨🇴

Una aplicación local FULL-LOCAL para preparación de exámenes de la DIAN.
Incluye banco de preguntas adaptativo, historial de intentos y seguimiento de debilidades.

## 🚀 Características
- **100% Local**: Datos guardados en SQLite en tu PC.
- **Adaptativo**: El algoritmo prioriza temas donde fallas.
- **Sin Costo**: Usa generadores de plantillas incluidos.
- **Opcional**: Conecta OpenAI/Gemini si tienes API Key.

## 🛠 Instalación

1. **Requisitos**: Python 3.10+ instalado.
2. **Setup**:
   ```bash
   # Crear entorno virtual (opcional pero recomendado)
   python -m venv venv
   # Activar: venv\Scripts\activate (Windows) o source venv/bin/activate (Mac/Linux)
   
   # Instalar dependencias
   pip install -r requirements.txt
   ```
3. **Inicializar Base de Datos**:
   ```bash
   # Esto crea la BD y carga 200 preguntas de ejemplo
   python scripts/init_db.py
   ```

## ▶️ Ejecución
```bash
streamlit run app/app.py
```
Abre tu navegador en `http://localhost:8501`.

## 📂 Estructura
- `app/`: Interfaz de usuario (Streamlit).
- `core/`: Lógica de negocio (algoritmos, deduplicación).
- `db/`: Modelos de datos y conexión.
- `scripts/`: Utilidades de mantenimiento.

## 🧪 Pruebas
Para desarrolladores o verificar integridad:
```bash
pytest tests/
```

## 📝 Importar tus Preguntas
Puedes subir un CSV en la sección "Banco de Preguntas" con las columnas:
`track, competency, topic, stem, options_A, options_B, options_C, options_D, correct_key, rationale`

---
**Nota**: Este software es una herramienta de práctica y no contiene preguntas filtradas reales.
