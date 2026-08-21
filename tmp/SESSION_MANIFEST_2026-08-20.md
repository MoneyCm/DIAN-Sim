# Session Manifest — 2026-08-20

## Changes Summary

### Code Changes (committed to Git)
| File | Change |
|------|--------|
| `tests/test_exam_claims_disclosure.py` | Fix: search for "Práctica PJS cronometrada" in `ui_utils.py` instead of `app.py` |
| `core/function_coverage.py` | Add `function_display_label()` and `function_display_detail()` helpers for standardized F1-F9 UI format |
| `app/pages/1_Nuevo_Simulacro.py` | Use standardized `F6 · Short name` format in "Ver Manual de Funciones" expander and practice selectbox |
| `app/pages/7_Configuracion_OPEC.py` | Use standardized format in "Revisar funciones" expander |
| `app/pages/14_Mis_OPEC.py` | Use standardized format in "Ver funciones" expander |

### Database Changes (Neon — not in Git)
| Action | Count | Details |
|--------|-------|---------|
| F9 → F6 reassignment | 10 | Questions about Decreto 1165 fiscalización aduanera moved from F9 to F6 |
| F9 → F4 reassignment | 2 | Questions about actos administrativos/notificación moved from F9 to F4 |
| F6 quarantine | 4 | Short stems/no rationale → moved to `bank_partition=reserved` |
| F4 reorder (A→B/C) | 12 | Balanced A=22, B=21, C=20 |
| F6 reorder (A→B/C) | 18 | Balanced A=38, B=34, C=33 |
| F3 reorder (A→B/C) | 1 | Balanced A=9, B=7, C=7 |
| F5 reorder (A→B/C) | 2 | Balanced A=9, B=10, C=7 |

### Key Distribution Before/After
| Fn | Before (%A) | After (%A) | max_diff Before | max_diff After |
|----|-------------|------------|-----------------|----------------|
| F1 | 37% | 37% | 6 | 6 |
| F2 | 39% | 39% | 3 | 3 |
| F3 | 43% | 39% | 4 | 2 |
| F4 | 54% | 35% | 23 | 2 |
| F5 | 42% | 35% | 6 | 3 |
| F6 | 53% | 36% | 33 | 5 |
| F7 | 20% | 20% | 8 | 8 |
| F8 | 32% | 32% | 5 | 5 |
| F9 | 29% | 29% | 3 | 4 |

### Test Results
- 606 passed, 6 failed (pre-existing: `test_learning_evidence_service` × 5, `test_simplified_navigation` × 1)
- `test_exam_claims_disclosure.py` now passes (was the 7th failure)

### Artifacts
- `tmp/rotation_manifest.json` — 37 reorder actions with question IDs and previews
- `tmp/reorder_manifest_f6f9.json` — Earlier pilot (superseded by rotation_manifest.json)

### UI Standardization
All function displays now use format: `F6 · Ejecución de acciones de fiscalización`
Full MERF text available in expanders via `function_display_detail()`.
Short names sourced from `data/opec_236769_matrix.json`.

### Not Done (pending)
- F7 key distribution (A=20% is low but acceptable — B-heavy is fine for this function)
- Further F6 rotation (18 of ~56 excess A rotated; remaining 18 could be done in future session)
- Normative reference verification for all questions
- Commit DB changes (profile update, scope assignments, question generation) — these live only in Neon
