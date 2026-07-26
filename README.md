# DianSim: Simulador de Concurso DIAN 🇨🇴

Aplicación Streamlit para preparar concursos DIAN mediante simulacros, práctica adaptativa, seguimiento de resultados y herramientas de IA.

## Funciones principales

- Simulacros por temas y simulacro tipo examen.
- Plan diario inteligente de 20 preguntas basado en debilidades, errores recurrentes y repasos pendientes.
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