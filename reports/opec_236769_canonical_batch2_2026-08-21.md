# Auditoría canónica OPEC 236769 — lote 2

Fecha de contraste: 2026-08-21

Alcance aprobado: 29 preguntas

Actor de trazabilidad: `codex/canonical-source-review-batch2-2026-08-21`

## Resultado editorial

El inventario vigente contiene 309 preguntas activas que aún no tenían
verificación canónica, no unas 589. De las 32 candidatas que reunían ancla
oficial, revisión humana histórica y estructura válida, se aprobaron 29 tras
contrastar individualmente su clave con la fuente oficial.

Tres candidatas no se aprobaron porque repiten casi el mismo aprendizaje que
otra pregunta del lote. No se borraron ni se cambiaron de partición:

- `5678fed2-1f03-43fe-b332-5cc2cd8d27f4`
- `99865a70-efe6-4c69-a5df-d98c80e0ae71`
- `06fc026c-f560-4dca-9768-1f04bb74cbde`

## Cobertura del lote

| Función | Preguntas aprobadas |
|---|---:|
| F4 · Actos administrativos | 12 |
| F5 · Revisión técnica y jurídica | 1 |
| F6 · Ejecución de acciones de fiscalización | 12 |
| F8 · Práctica de pruebas | 4 |
| **Total** | **29** |

## Correcciones de contenido

Dos preguntas atribuían al parágrafo del artículo 260-5 del Estatuto
Tributario la prioridad de los comparables internos. El texto está en el
parágrafo del artículo 260-4. Se corrigieron únicamente la justificación y la
referencia, sin cambiar el caso, el enunciado, las opciones ni la clave:

- `74ab6e63-2575-4d8e-9d5f-3cfa1080eaa4`
- `b49aba7d-f513-4295-8385-d9686bbb75d7`

## Fuentes oficiales contrastadas

- Estatuto Tributario, compilación jurídica DIAN.
- Decreto 1165 de 2019, compilación jurídica DIAN.
- Ley 1437 de 2011 (CPACA), compilación jurídica DIAN.
- Concepto DIAN 018477 interno 2191 de 2025.
- Procedimiento DIAN PR-COT-0432, versión 3.

La migración idempotente conserva fuera de entrega cualquier pregunta que no
esté incluida expresamente en este lote. Tampoco promueve preguntas que hayan
sido movidas a una partición distinta de `training`.
