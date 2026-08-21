# Session Manifest — 2026-08-20 (v2)

## Changes Summary

### Code Changes (commit `5599819`)
| File | Change |
|------|--------|
| `tests/test_exam_claims_disclosure.py` | Fix: search "Practica PJS cronometrada" in `ui_utils.py` (was `app.py`) |
| `core/function_coverage.py` | Add `function_display_label()`, `function_display_detail()`, fix `_load_short_names()` to handle any OPEC number |
| `app/pages/1_Nuevo_Simulacro.py` | Standardized `F6 · Short name` format in expander + selectbox |
| `app/pages/7_Configuracion_OPEC.py` | Standardized format in "Revisar funciones" |
| `app/pages/14_Mis_OPEC.py` | Standardized format in "Ver funciones" |

### Database Changes (Neon — idempotent migration in `migrations/`)
| Action | Count | Details |
|--------|-------|---------|
| F9 -> F6 reassignment | 10 | Decreto 1165 fiscalizacion aduanera questions |
| F9 -> F4 reassignment | 2 | Actos administrativos / notificacion |
| F6 quarantine | 4 | Short stems / no rationale -> `bank_partition=reserved` |
| Key rotation (v2, training only) | 12 | Minimal: F7(4), F1(2), F8(2), F9(2), F6(1), F3(1) |

### Key Distribution (training only, after v2 rotation)
| Fn | Total | A | B | C | max_diff |
|----|-------|---|---|---|----------|
| F1 | 19 | 7 (37%) | 7 (37%) | 5 (26%) | 2 |
| F2 | 18 | 7 (39%) | 7 (39%) | 4 (22%) | 3 |
| F3 | 23 | 8 (35%) | 7 (30%) | 8 (35%) | 1 |
| F4 | 63 | 22 (35%) | 21 (33%) | 20 (32%) | 2 |
| F5 | 26 | 9 (35%) | 10 (38%) | 7 (27%) | 3 |
| F6 | 101 | 35 (35%) | 33 (33%) | 33 (33%) | 2 |
| F7 | 25 | 8 (32%) | 9 (36%) | 8 (32%) | 1 |
| F8 | 34 | 11 (32%) | 12 (35%) | 11 (32%) | 1 |
| F9 | 35 | 12 (34%) | 12 (34%) | 11 (31%) | 1 |

### Test Results
- 606 passed, 6 failed (pre-existing: `test_learning_evidence_service` x5, `test_simplified_navigation` x1)
- `test_exam_claims_disclosure.py` now passes

### Artifacts
- `migrations/manifest_2026-08-20_rotation.json` — 12 reorder actions with question IDs
- `migrations/apply_rotation_2026-08-20.py` — Idempotent migration script (--dry-run supported)
- `tmp/rotation_manifest_v2.json` — Working copy (same content as migrations version)

### Pending
- Normative reference verification for all questions
- Commit DB changes (profile update, scope assignments, question generation) to Git
