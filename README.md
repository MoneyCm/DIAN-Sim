# DIAN Sim: preparación personalizada para concursos 🇨🇴

Aplicación Streamlit para preparar concursos mediante práctica PJS, estudio adaptativo, seguimiento verificable y herramientas opcionales de IA. No es un producto oficial de la DIAN ni de la CNSC y no garantiza obtener el empleo.

## Funciones principales

- Identidad y aislamiento por usuario, concurso y OPEC activa.
- Diagnóstico equilibrado por funciones, práctica recomendada, por tema, competencia, función, errores y máxima exigencia.
- Práctica PJS cronometrada con política interna versionada; cantidad y duración oficiales permanecen vacías mientras no estén publicadas.
- Afirmaciones comportamentales e integridad en escala Likert de cuatro opciones, sin clave correcta.
- Dificultad editorial interna 1–10, exposición controlada y repaso espaciado basado en evidencia.
- Plan diario explicable según debilidades, errores, repaso pendiente, tiempo disponible y fecha objetivo.
- Tutor socrático con razonamiento del usuario, fuente trazable y funcionamiento local sin depender de IA.
- Cuaderno de errores con causa, regla, microlección y superación por transferencia diferida.
- Biblioteca de estudio que separa núcleo oficial de corpus editorial relacionado.
- Banco con revisiones inmutables, citas precisas y particiones `training`, `measurement`, `anchor` y `reserved`.
- Readiness por puertas transparentes y objetivo interno editable; el mínimo oficial se muestra por separado.
- Exportación Anki, búsqueda normativa e IA opcional con cuotas y límites persistentes.
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

En desarrollo local la aplicación usa `dian_sim.db` cuando no encuentra
`DATABASE_URL`. En producción configura `DIAN_SIM_ENV=production` o
`REQUIRE_DATABASE_URL=true`: el arranque falla de forma segura si falta la base
remota y nunca cambia silenciosamente a SQLite.

El arranque no genera bancos grandes. `AUTO_SEED_OPEC_BANKS=true` queda
reservado para una operación administrativa explícita; en producción debe
permanecer desactivado durante el tráfico normal.

## Pruebas

```powershell
python -m pytest -q
```

## Tutor adaptativo e IA opcional

En SQLite de desarrollo las tablas aditivas se crean al arrancar. En una base
persistente o remota usa exclusivamente los preflight y migradores versionados
de [`docs/DESPLIEGUE_FASE_1.md`](docs/DESPLIEGUE_FASE_1.md); todos son *dry-run*
por defecto.

El tutor funciona sin IA. Los proveedores y modelos habilitados se configuran
mediante secretos o desde la administración autorizada. Dominio, prioridad,
repaso, dificultad y selección nunca dependen del modelo.

## Estructura

- `app/`: interfaz Streamlit y páginas.
- `core/`: autenticación, adaptación, IA, RAG y Anki.
- `db/`: modelos y conexión SQLAlchemy.
- `services/`: lógica de preguntas, estadísticas y pagos.
- `scripts/`: administración, generación, verificación y mantenimiento.
- `tests/`: pruebas automatizadas.

## Seguridad

Las páginas de administración y diagnóstico requieren un usuario cuyo rol persistido sea `admin`. Las claves guardadas desde la aplicación se cifran antes de almacenarse en la base de datos. En producción se deben suministrar secretos mediante Streamlit Secrets o variables de entorno y mantener estable `DIAN_SIM_FERNET_KEY` entre despliegues.

Las migraciones aditivas de identidad/alcance OPEC, evidencia pedagógica y
política de simulacros se ejecutan primero en modo diagnóstico. Consulta
[`docs/DESPLIEGUE_FASE_1.md`](docs/DESPLIEGUE_FASE_1.md) antes de aplicarla.

> Este software es una herramienta de práctica y no contiene preguntas filtradas reales.
