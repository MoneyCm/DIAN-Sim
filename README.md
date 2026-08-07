# DianSim: Simulador de Concurso DIAN 🇨🇴

Aplicación Streamlit para preparar concursos DIAN mediante simulacros, práctica adaptativa, seguimiento de resultados y herramientas de IA.

## Funciones principales

- Simulacros por temas y simulacro tipo examen.
- Plan diario inteligente de 20 preguntas basado en debilidades, errores recurrentes y repasos pendientes.
- Repaso espaciado nativo con cola diaria, nivel de confianza y clasificación de errores; Anki queda como exportación opcional.
- Preparación multi-concurso CNSC con catálogo de procesos, OPEC activa y bancos/progreso separados por concurso.
- Sesiones guiadas por tiempo, fecha de examen y disponibilidad semanal, con una estructura recomendada de 30 minutos.
- Tutor adaptativo V1 con sesiones persistentes, dominio por tema, seguridad, causa de error y selección de una pregunta a la vez.
- Router opcional de IA con salida estructurada y fallback determinístico.
- Motivación basada en progreso real: misión semanal flexible, cobertura del temario, mapa de dominio y cierre diario.
- Motor adaptativo para simulacros configurables.
- Banco de preguntas, casos situacionales y módulo de ética.
- Exportación Anki y enriquecimiento pedagógico opcional mediante IA.
- Consulta RAG sobre normativa indexada.
- Autenticación local y Google OIDC opcional.
- SQLite para uso local o PostgreSQL/Neon mediante `DATABASE_URL`.

## Instalación

Requiere Python 3.10 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y configura únicamente las variables que vayas a utilizar. Los secretos no deben incluirse en Git.

## Ejecución

```powershell
streamlit run app/app.py
```

La aplicación usa `dian_sim.db` cuando no encuentra `DATABASE_URL`. El esquema se sincroniza durante el arranque por compatibilidad con las instalaciones existentes.

## Pruebas

```powershell
python -m pytest -q
```

## Tutor adaptativo e IA opcional

Las tablas se crean automáticamente en SQLite. También puede ejecutarse la migración explícita:

```powershell
.\.venv\Scripts\python.exe scripts\data\migrate_learning_v1.py
```

El tutor funciona sin IA. Para usar la cuota gratuita configura `AI_PROVIDER=gemini`,
`GEMINI_API_KEY` y `gemini-3.6-flash` en los tres perfiles. Si existe una clave de
Gemini y no se especifica proveedor, el router la detecta automáticamente. También
admite OpenAI. Dominio, prioridad, repaso y selección nunca dependen del modelo.

## Estructura

- `app/`: interfaz Streamlit y páginas.
- `core/`: autenticación, adaptación, IA, RAG y Anki.
- `db/`: modelos y conexión SQLAlchemy.
- `services/`: lógica de preguntas, estadísticas y pagos.
- `scripts/`: administración, generación, verificación y mantenimiento.
- `tests/`: pruebas automatizadas.

## Seguridad

Las páginas de administración y diagnóstico requieren un usuario cuyo rol persistido sea `admin`. Las claves guardadas desde la aplicación se cifran antes de almacenarse en la base de datos. En producción se deben suministrar secretos mediante Streamlit Secrets o variables de entorno y mantener estable `DIAN_SIM_FERNET_KEY` entre despliegues.

> Este software es una herramienta de práctica y no contiene preguntas filtradas reales.
