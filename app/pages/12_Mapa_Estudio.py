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
    def build_function_study_map(functions, questions, performances):
        rows, unmatched = build_function_coverage(functions, questions, performances)
        for row in rows:
            row["sources"] = []
            row["recommendation"] = "Actualiza la aplicación para ver el mapa de fuentes verificadas."
        return rows, unmatched
from core.legacy_question_audit import is_safe_for_active_study
from db.models import Question, QuestionPerformance, UserOPEC
from db.session import SessionLocal
from ui_utils import load_css, render_custom_sidebar, render_header


if not AuthManager.check_auth():
    st.warning("Inicia sesión para ver tu mapa de estudio.")
    st.stop()

load_css()
render_custom_sidebar()
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
        st.page_link("pages/7_Configuracion_OPEC.py", label="Configurar mi OPEC", icon="⚙️")
        st.stop()

    functions = active_opec.functions if isinstance(active_opec.functions, list) else []
    if not functions:
        st.warning("Tu ficha no tiene funciones cargadas. Agrégalas para vincular fuentes y preguntas.")
        st.page_link("pages/7_Configuracion_OPEC.py", label="Completar funciones de la ficha", icon="📋")
        st.stop()

    questions = db.query(Question).filter(
        Question.competition_id == competition_id,
    ).all()
    questions = [question for question in questions if is_safe_for_active_study(question)]
    performances = db.query(QuestionPerformance).join(Question).filter(
        QuestionPerformance.user_id == user_id,
        Question.competition_id == competition_id,
    ).all()
    rows, unmatched = build_function_study_map(functions, questions, performances)

    st.info(
        f"Concurso: **{competition.name if competition else 'Sin concurso'}** · "
        f"OPEC {active_opec.opec_number} · {len(questions)} preguntas aptas analizadas."
    )
    st.caption(
        "Una función se considera con evidencia cuando tiene preguntas verificadas y ya has "
        "practicado al menos tres. Las fuentes mostradas pertenecen únicamente a preguntas verificadas."
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
                st.markdown("**Fuentes verificadas para estudiar:**")
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
