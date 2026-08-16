import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competitions import get_active_competition, get_active_competition_id
from core.function_coverage import build_function_coverage
try:
    from core.function_coverage import build_function_study_map
except ImportError:
    def build_function_study_map(functions, questions, performances, catalog_sources=None):
        rows, unmatched = build_function_coverage(functions, questions, performances)
        for row in rows:
            row["sources"] = list((catalog_sources or {}).get(row["function_number"], []))
            row["recommendation"] = "Actualiza la aplicación para ver el mapa de fuentes verificadas."
        return rows, unmatched
from core.opec_source_catalog import sources_for_opec_function
from core.preparation_matrix import build_master_preparation_matrix
from core.learning.evidence_service import evaluate_opec_readiness
from core.readiness_gate import (
    OFFICIAL_FUNCTIONAL_MINIMUM_SCORE,
    ReadinessPolicy,
)
from db.models import OpecStudyPlan, Question, QuestionPerformance, UserOPEC
from db.session import SessionLocal
from services.question_service import QuestionService
from ui_utils import load_css, render_header


READINESS_GATE_LABELS = {
    "trusted_sources_and_bank": "Fuentes y banco confiables",
    "measurement_session_count": "Tres mediciones comparables",
    "measurement_partition": "Partición exclusiva de medición",
    "completed_sessions": "Sesiones completas",
    "no_feedback_or_aids": "Sin retroalimentación ni ayudas",
    "same_versioned_context": "Misma OPEC y versiones",
    "recent_sessions": "Mediciones recientes",
    "minimum_functional_total": "Mínimo funcional por sesión",
    "functional_precision_target": "Objetivo interno de precisión",
    "joint_function_coverage": "Cobertura conjunta de nueve funciones",
    "no_repeated_measurement_material": "Sin casos ni revisiones repetidos",
}


def _load_readiness_state(db, *, user_id, active_opec):
    """Load internal readiness and fail closed while Phase 2 data is absent."""
    target_score = 85.0
    notes = []
    if user_id is None or active_opec is None:
        return target_score, None, "Activa una OPEC para iniciar la medición interna."

    try:
        plan = db.query(OpecStudyPlan).filter_by(
            user_id=user_id,
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
        ).first()
        if plan is not None:
            configured_target = float(plan.target_score)
            if 0.0 <= configured_target <= 100.0:
                target_score = configured_target
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        notes.append("Se usa temporalmente el objetivo interno predeterminado de 85%.")

    try:
        assessment = evaluate_opec_readiness(
            db,
            user_id=user_id,
            user_opec_id=active_opec.id,
            policy=ReadinessPolicy(target_score=target_score),
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        notes.append(
            "Las sesiones canónicas de medición aún no están disponibles; "
            "las puertas permanecen pendientes."
        )
        return target_score, None, " ".join(notes)
    return target_score, assessment, " ".join(notes) or None


if not AuthManager.check_auth():
    st.warning("Inicia sesión para ver tu mapa de estudio.")
    st.stop()

load_css()
render_header(
    title="Mapa de estudio por ficha",
    subtitle="Fuentes verificadas, cobertura y siguiente acción para cada función",
)

user_id = st.session_state.get("user_id")
db = SessionLocal()
try:
    active_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()
    competition = get_active_competition(db, user_id)
    competition_id = get_active_competition_id(db, user_id)

    if not active_opec:
        st.warning("Primero configura una OPEC activa para construir tu mapa de estudio.")
        st.page_link("pages/15_Centro_OPEC.py", label="Configurar mi OPEC", icon="⚙️")
        st.stop()

    functions = active_opec.functions if isinstance(active_opec.functions, list) else []
    if not functions:
        st.warning("Tu ficha no tiene funciones cargadas. Agrégalas para vincular fuentes y preguntas.")
        st.page_link("pages/15_Centro_OPEC.py", label="Completar funciones de la ficha", icon="📋")
        st.stop()

    readiness_target, readiness_assessment, readiness_note = _load_readiness_state(
        db, user_id=user_id, active_opec=active_opec
    )

    questions = QuestionService.get_questions_for_user(
        db,
        user_id,
        competition_id=competition_id,
        user_opec=active_opec,
        bank_partitions=("training",),
    )
    question_ids = [question.question_id for question in questions]
    performances = db.query(QuestionPerformance).join(Question).filter(
        QuestionPerformance.user_id == user_id,
        Question.competition_id == competition_id,
        Question.question_id.in_(question_ids),
    ).all()
    catalogue = {
        index: sources_for_opec_function(active_opec.opec_number, function)
        for index, function in enumerate(functions, start=1)
    }
    rows, unmatched = build_function_study_map(
        functions, questions, performances, catalogue
    )
    master_matrix = build_master_preparation_matrix(
        active_opec.opec_number, functions, questions, performances
    )

    st.info(
        f"Concurso: **{competition.name if competition else 'Sin concurso'}** · "
        f"OPEC {active_opec.opec_number} · {len(questions)} preguntas aptas analizadas."
    )
    st.markdown("### Estado prudente de preparación")
    readiness_cols = st.columns(3)
    readiness_cols[0].metric(
        "Objetivo interno de precisión", f"{readiness_target:.0f}%"
    )
    readiness_cols[1].metric(
        "Mediciones comparables",
        (
            readiness_assessment.repeated_target_label.replace(
                "meta interna repetida ", ""
            )
            if readiness_assessment is not None
            else "0/3"
        ),
    )
    readiness_cols[2].metric(
        "Mínimo oficial funcional",
        f"{OFFICIAL_FUNCTIONAL_MINIMUM_SCORE:.0f}/100",
    )
    if readiness_assessment is None:
        st.info(
            "Las puertas permanecen pendientes hasta contar con mediciones canónicas "
            "completas y comparables."
        )
    elif readiness_assessment.internal_precision_goal_met:
        st.success(
            f"{readiness_assessment.repeated_target_label.capitalize()}. "
            "La retención diferida conserva una puerta independiente."
        )
    else:
        st.info("La evidencia interna aún está en construcción.")

    if readiness_note:
        st.caption(readiness_note)
    st.caption(
        "El objetivo interno de precisión orienta el estudio y no sustituye la calificación "
        "oficial. El 70/100 se muestra por separado como mínimo funcional de DIAN 2676; "
        "no es una predicción de aprobación ni de posición en la lista."
    )
    if readiness_assessment is not None:
        with st.expander("Puertas transparentes de la medición", expanded=False):
            for gate in readiness_assessment.gates:
                icon = "✅" if gate.met else "⏳"
                label = READINESS_GATE_LABELS.get(gate.key, gate.key)
                st.markdown(f"- {icon} **{label}**")
                if not gate.met and gate.reasons:
                    st.caption(gate.reasons[0])
            retention = readiness_assessment.retention_gate
            retention_icon = "✅" if retention.met else "⏳"
            st.markdown(f"- {retention_icon} **retención diferida**")
            if retention.reasons:
                st.caption(retention.reasons[0])

    if master_matrix.get("available"):
        st.markdown("### Matriz maestra de preparación")
        summary_cols = st.columns(2)
        summary_cols[0].metric(
            "Cobertura confiable",
            f"{master_matrix['trusted_question_count']} / {master_matrix['functional_question_target']}",
        )
        summary_cols[1].metric(
            "Funciones en riesgo alto", master_matrix["high_risk_functions"]
        )
        st.progress(master_matrix["coverage_ratio"])
        st.warning(
            "Las metas de 1.500/400/300 son objetivos editoriales de construcción, no cantidades "
            "ni ponderaciones oficiales del examen. La GOA, duración, ejes y número de ítems del "
            "cuadernillo DIAN 2676 siguen pendientes de publicación."
        )
        st.caption(master_matrix.get("exam_format_status") or "")

        for row in master_matrix["rows"]:
            risk_icon = {"Alto": "🔴", "Medio": "🟠", "Bajo": "🟢"}.get(row["risk"], "⚪")
            title = f"{risk_icon} F{row['number']} · {row['short_name']} — {row['coverage_status']}"
            with st.expander(title, expanded=row["risk"] == "Alto"):
                metric_cols = st.columns(3)
                metric_cols[0].metric(
                    "Preguntas con evidencia completa",
                    f"{row['trusted_question_count']} / {row['functional_question_target']}",
                )
                metric_cols[1].metric("Casos situacionales", row["case_count"])
                metric_cols[2].metric(
                    "Estimación interna de desempeño",
                    f"{row['mastery'] * 100:.0f}%",
                )
                st.write(f"**Función MERF:** {row['function']}")
                st.write(f"**Siguiente acción:** {row['next_action']}")
                if row.get("knowledge"):
                    st.markdown("**Conocimientos y subtemas derivados para preparar:**")
                    st.markdown("\n".join(f"- {item}" for item in row["knowledge"]))
                if row.get("situation_types"):
                    st.markdown("**Situaciones laborales a entrenar:**")
                    st.markdown("\n".join(f"- {item}" for item in row["situation_types"]))
                if row.get("cognitive_levels"):
                    st.caption("Niveles cognitivos editoriales: " + ", ".join(row["cognitive_levels"]))
                if row["sources"]:
                    st.markdown("**Fuentes oficiales vinculadas:**")
                    for source in row["sources"]:
                        st.markdown(
                            f"- [{source['name']}]({source['url']}) — {source['locators']} · "
                            f"{source['validity']} (consulta {source['consulted_on']})"
                        )
                else:
                    st.error("No hay una fuente oficial vinculada; este bloque no puede declararse cubierto.")
    else:
        st.caption(
            "Una función se considera con evidencia cuando tiene preguntas verificadas y ya has "
            "practicado al menos tres. Las fuentes mostradas provienen de preguntas verificadas o del catálogo oficial de la OPEC."
        )

        for row in rows:
            status_icon = {
                "Con evidencia": "✅",
                "Pendiente de práctica": "📝",
                "Revisar calidad": "🔎",
                "Faltan preguntas": "⚠️",
            }.get(row["status"], "📌")
            with st.expander(f"{status_icon} {row['label']} — {row['status']}", expanded=row["status"] != "Con evidencia"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Preguntas", row["questions"])
                col2.metric("Verificadas", row["trusted"])
                col3.metric("Con práctica", row["practiced"])
                st.write(f"**Siguiente paso:** {row['recommendation']}")
                if row["sources"]:
                    st.markdown("**Fuentes recomendadas para estudiar:**")
                    for source in row["sources"]:
                        st.markdown(f"- {source}")
                else:
                    st.warning("No hay fuente verificada vinculada. No generes preguntas nuevas hasta cargar la fuente oficial.")

    if unmatched:
        st.caption(
            f"{unmatched} pregunta(s) no se asociaron a una función por falta de coincidencia suficiente; "
            "no se usan para inflar la cobertura."
        )
finally:
    db.close()
