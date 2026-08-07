# Tutor adaptativo V1

La V1 amplía la arquitectura existente sin sustituir Streamlit, SQLAlchemy,
la autenticación, el catálogo multi-concurso ni el banco de preguntas.

## Flujo

1. `LearningSessionService.start_learning_session()` crea una sesión y consulta
   únicamente las preguntas del concurso activo.
2. El motor determinístico calcula la prioridad de cada tema y selecciona una
   pregunta. No prepara la sesión completa por adelantado.
3. `submit_answer()` califica la opción múltiple, registra el intento, actualiza
   dominio y repaso, y solo entonces selecciona la siguiente pregunta.
4. `TutorService` puede enriquecer la explicación con IA. Si la llamada falla,
   conserva la calificación y explicación determinísticas.

## Fórmula de prioridad

Todos los factores se normalizan entre 0 y 1:

```text
prioridad = 0.35 × brecha_dominio
          + 0.20 × revision_vencida
          + 0.20 × tasa_error_reciente
          + 0.10 × tasa_seguridad_baja
          + 0.10 × importancia
          + 0.05 × tiempo_sin_estudiar
```

El dominio usa una media móvil transparente:

```text
nuevo = actual + (0.20 × fuerza_seguridad) × (resultado - actual)
```

`resultado` vale 1.0 para correcta, 0.6 para parcial y 0.0 para incorrecta.
La fuerza de seguridad es 0.80, 1.00 o 1.10 para baja, media o alta.

## Seguridad del agente

El modelo no recibe conexión ni consultas SQL. `TutorTools` expone operaciones
limitadas, con usuario y concurso fijados por la aplicación. Las preguntas no
incluyen solución antes de responder. La IA no puede cambiar una calificación
determinística ni insertar preguntas en el banco oficial.

## Modelos y fallback

Los perfiles se configuran con `MODEL_FAST`, `MODEL_BALANCED` y
`MODEL_REASONING`. El router admite OpenAI y Gemini. Si encuentra una clave Gemini
sin proveedor explícito, selecciona automáticamente `gemini-3.6-flash`, que cuenta
con nivel gratuito sujeto a cuota. En ausencia de proveedor, clave, respuesta
válida o servicio, la sesión continúa con selección múltiple, persistencia,
dominio y repaso.

La tabla `ai_call_logs` conserva proveedor, modelo, tarea, versión de prompt,
tokens cuando están disponibles, latencia, resultado y fecha. No almacena
prompts, respuestas, claves ni secretos.
