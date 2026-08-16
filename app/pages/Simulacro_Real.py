
import streamlit as st
import datetime
import os
import sys
import unicodedata

# ruff: noqa: E402 -- Streamlit ejecuta la página como script independiente.

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import joinedload
from sqlalchemy import inspect
from db.session import get_db
from db.models import (
    CaseStudy,
    Competition,
    OpecLearningEvent,
    OpecLearningSession,
    OpecProfile,
    OpecSimulationPolicy,
    OpecStudyPlan,
    Question,
    UserOPEC,
)
from ui_utils import escape_html, load_css as inject_custom_css, log_ui_exception
from services.question_service import QuestionService
from services.stats_service import StatsService
from core.auth import AuthManager
from core.exam_format import (
    build_trusted_pjs_case_blocks,
    is_trusted_pjs_case,
)
from core.exposure_control import (
    block_is_novel,
    exposure_snapshot,
    select_novel_measurement_blocks,
)
from core.question_opec_scope import question_matches_opec
from core.real_exam import blueprint_for_competition
from core.learning.evidence_service import (
    evaluate_opec_readiness,
    finalize_opec_session,
    record_opec_event,
    start_opec_session,
)
from core.readiness_gate import ReadinessPolicy
from core.simulation_policy import (
    ResolvedSimulationPolicy,
    SimulationPolicyValidationError,
    resolve_active_policy,
)
from core.session_results import save_last_result

# --- CONFIGURACIÓN DE PÁGINA ---
# pass # Removed st.set_page_config

# --- VERIFICACIÓN DE AUTENTICACIÓN ---
if not AuthManager.check_auth():
    st.warning("⚠️ Inicia sesión para acceder a la práctica PJS cronometrada.")
    st.info("La autenticación permite guardar el progreso y los resultados de práctica.")
    st.stop()

inject_custom_css()

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
<style>
    .case-text {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2e86c1;
        font-family: 'Georgia', serif;
        font-size: 1.1rem;
        line-height: 1.6;
        color: #2c3e50;
        height: auto;
        max-height: 60vh;
        overflow-y: auto;
    }
    .timer-box {
        background-color: #e74c3c;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        font-size: 1.5rem;
        position: fixed;
        top: 60px;
        right: 20px;
        z-index: 999;
    }
    .question-box {
        margin-bottom: 30px;
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- FOCUS MODE CSS (Modo examen concentrado) ---
st.markdown("""
<style>
    [data-testid="stHeader"] { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .main .block-container {
        max-width: 760px !important;
        padding-top: 0.7rem !important;
    }
    .stButton button {
        border-radius: 10px !important;
    }
    div[data-testid="stColumn"],
    div[data-testid="column"] {
        width: 100% !important;
        flex: 0 0 100% !important;
        max-width: 100% !important;
    }
    .case-text {
        margin-bottom: 1rem !important;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
        max-height: 62vh !important;
    }
    [data-testid="stRadio"] label {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .main .block-container > div > div {
        gap: 0.6rem !important;
    }
    .timer-box {
        top: 0.5rem !important;
        right: 0.8rem !important;
        position: sticky !important;
        margin-bottom: 0.8rem !important;
        z-index: 11 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "exam_active" not in st.session_state:
    st.session_state.exam_active = False
if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = None
if "exam_cases" not in st.session_state:
    st.session_state.exam_cases = []
if "current_case_idx" not in st.session_state:
    st.session_state.current_case_idx = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {} # {question_id: choice}
if "exam_competition_id" not in st.session_state:
    st.session_state.exam_competition_id = None
if "exam_opec_number" not in st.session_state:
    st.session_state.exam_opec_number = None
if "exam_marked_questions" not in st.session_state:
    st.session_state.exam_marked_questions = []


def _phase2_evidence_available(db):
    required = {
        "question_revisions",
        "opec_learning_sessions",
        "opec_learning_events",
        "opec_topic_states",
        "error_episodes",
    }
    return required.issubset(set(inspect(db.connection()).get_table_names()))

BANNED_SIM_REAL_TERMS = [
    "comision nacional del servicio civil",
    "cnsc",
    "constructora horizonte",
    "constructora soluciones sas",
    "alcaldia municipal",
    "alcalde de villaflores",
    "villaflores",
    "san vicente",
    "lpn-2023-054",
    "contratacion publica",
    "obra publica",
    "licitacion publica",
    "ley 80 de 1993",
    "centro de salud de tercer nivel",
    "procuraduria",
    "fiscalia",
    "dumping",
    "sobornos",
    "campana electoral",
    "sipr",
    "horizonte s.a.",
    "horizonte sa",
    "lpn 2023",
]


def _normalize_exam_text(value):
    value = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _block_matches_opec(case, opec_number, eligible_question_ids=None):
    questions = list(getattr(case, "questions", None) or [])
    if not questions:
        return False
    target = str(opec_number or "").strip()
    tagged_scope = str(getattr(case, "opec_number", "") or "").strip()
    if tagged_scope and tagged_scope != target:
        return False
    if eligible_question_ids is not None:
        return all(
            str(getattr(question, "question_id", "") or "")
            in eligible_question_ids
            for question in questions
        )
    if tagged_scope:
        return tagged_scope == target
    return all(question_matches_opec(question, target) for question in questions)


def _same_exam_context(stored_competition, stored_opec, active_competition, active_opec):
    if stored_competition is None or active_competition is None:
        return False
    try:
        same_competition = int(stored_competition) == int(active_competition)
    except (TypeError, ValueError):
        return False
    return same_competition and (
        str(stored_opec or "").strip() == str(active_opec or "").strip()
    )


def _case_is_valid_for_opec(case, opec_number, eligible_question_ids=None):
    if not is_trusted_pjs_case(case):
        return False
    if not _block_matches_opec(case, opec_number, eligible_question_ids):
        return False
    questions = getattr(case, "questions", []) or []
    haystack_parts = [case.title, case.text, getattr(case, "topic", "")]
    for question in questions:
        haystack_parts.extend([
            getattr(question, "stem", ""),
            getattr(question, "rationale", ""),
            getattr(question, "topic", ""),
            getattr(question, "competency", ""),
        ])

    haystack = " ".join(_normalize_exam_text(part) for part in haystack_parts if part)
    if not haystack:
        return False

    # El concurso se limita en la consulta y cada pregunta debe declarar la
    # misma OPEC activa antes de entrar a inventario, sesión o revisión.
    return True


def _active_opec_scope(db, user_id):
    if not user_id:
        return None, None
    active_opec = (
        db.query(UserOPEC)
        .filter_by(user_id=user_id, is_active=True)
        .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .first()
    )
    if active_opec is None or active_opec.competition_id is None:
        return None, None
    opec_number = str(active_opec.opec_number or "").strip()
    return (active_opec.competition_id, opec_number) if opec_number else (None, None)


def _profile_function_count(profile):
    functions = getattr(profile, "functions", None)
    if isinstance(functions, list):
        return len(functions) or None
    if isinstance(functions, dict):
        nested = functions.get("functions")
        if isinstance(nested, (list, dict)):
            return len(nested) or None
        return len(functions) or None
    return None


def _simulation_policy_for_scope(
    db,
    competition_id,
    opec_number,
) -> tuple[object | None, ResolvedSimulationPolicy]:
    """Resolve one exact OPEC policy or a disclosed provisional fallback."""

    profile = None
    records = []
    table_names = set(inspect(db.connection()).get_table_names())
    if "opec_profiles" in table_names:
        profile = (
            db.query(OpecProfile)
            .filter_by(
                competition_id=int(competition_id),
                opec_number=str(opec_number),
            )
            .first()
        )
    if profile is not None and "opec_simulation_policies" in table_names:
        records = (
            db.query(OpecSimulationPolicy)
            .filter_by(opec_profile_id=profile.id)
            .order_by(OpecSimulationPolicy.version_number.desc())
            .all()
        )
    return profile, resolve_active_policy(
        records,
        opec_number=opec_number,
        function_count=_profile_function_count(profile),
    )


def _policy_blueprint(db, competition_id, opec_number, reviewed_case_count=None):
    competition = db.get(Competition, competition_id) if competition_id else None
    _, policy = _simulation_policy_for_scope(db, competition_id, opec_number)
    full_mode = policy.internal.mode("full")
    blueprint = blueprint_for_competition(
        getattr(competition, "code", None),
        reviewed_case_count=reviewed_case_count,
        target_question_count=full_mode.question_count,
        questions_per_case=policy.internal.max_questions_per_case,
        minutes_per_question=policy.internal.minutes_per_question,
        navigation_mode=policy.internal.navigation_mode,
    )
    return competition, blueprint, policy


def _eligible_question_ids(
    db,
    user_id,
    competition_id,
    opec_number,
    *,
    partition,
    include_review=False,
):
    user_opec = (
        db.query(UserOPEC)
        .filter_by(
            user_id=user_id,
            competition_id=competition_id,
            opec_number=str(opec_number),
            is_active=True,
        )
        .first()
    )
    if user_opec is None:
        return set()
    questions = QuestionService.get_questions_for_user(
        db,
        user_id,
        include_review=include_review,
        competition_id=competition_id,
        user_opec=user_opec,
        bank_partitions=(partition,),
    )
    return {
        str(getattr(question, "question_id", "") or "")
        for question in questions
    }


def _reviewed_blocks_for_opec(cases, opec_number, eligible_question_ids):
    return build_trusted_pjs_case_blocks(
        cases,
        eligible_question_ids=eligible_question_ids,
        opec_number=opec_number,
        bank_partition="measurement",
    )


def _reviewed_inventory():
    """Return reviewed, pending and unseen measurement counts for the OPEC."""
    db = next(get_db())
    try:
        competition_id, opec_number = _active_opec_scope(
            db, st.session_state.get("user_id")
        )
        if competition_id is None or not opec_number:
            return 0, 0, 0
        query = db.query(CaseStudy).options(joinedload(CaseStudy.questions))
        query = query.filter(CaseStudy.competition_id == competition_id)
        cases = query.all()
        measurement_ids = _eligible_question_ids(
            db,
            st.session_state.get("user_id"),
            competition_id,
            opec_number,
            partition="measurement",
        )
        training_ids = _eligible_question_ids(
            db,
            st.session_state.get("user_id"),
            competition_id,
            opec_number,
            partition="training",
            include_review=True,
        )
        blocks = _reviewed_blocks_for_opec(cases, opec_number, measurement_ids)
        relevant_cases = [
            case for case in cases
            if any(
                str(getattr(question, "question_id", "") or "") in training_ids
                for question in (getattr(case, "questions", None) or [])
            )
        ]
        reviewed_source_ids = {
            str(getattr(question, "case_id", "") or "")
            for block in blocks
            for question in block.questions
        }
        reviewed_sources = sum(
            1 for case in relevant_cases
            if str(getattr(case, "id", "") or "") in reviewed_source_ids
        )
        prior_events = []
        if _phase2_evidence_available(db):
            prior_events = (
                db.query(OpecLearningEvent)
                .join(
                    OpecLearningSession,
                    OpecLearningEvent.session_id == OpecLearningSession.id,
                )
                .filter(
                    OpecLearningEvent.user_id == st.session_state.get("user_id"),
                    OpecLearningSession.competition_id == competition_id,
                    OpecLearningSession.opec_number == str(opec_number),
                    OpecLearningSession.mode == "measurement",
                    OpecLearningSession.bank_partition == "measurement",
                    OpecLearningSession.status == "completed",
                )
                .all()
            )
        snapshot = exposure_snapshot(prior_events)
        novel_count = sum(block_is_novel(block, snapshot) for block in blocks)
        return (
            len(blocks),
            max(0, len(relevant_cases) - reviewed_sources),
            novel_count,
        )
    finally:
        db.close()


def _active_exam_context(reviewed_case_count=None):
    db = next(get_db())
    try:
        competition_id, opec_number = _active_opec_scope(
            db, st.session_state.get("user_id")
        )
        if competition_id is None or not opec_number:
            return None, None, None
        return _policy_blueprint(
            db,
            competition_id,
            opec_number,
            reviewed_case_count=reviewed_case_count,
        )
    finally:
        db.close()

def _reset_invalid_exam_state(clear_review=False):
    st.session_state.exam_cases = []
    st.session_state.exam_active = False
    st.session_state.current_case_idx = 0
    st.session_state.user_answers = {}
    st.session_state.exam_competition_id = None
    st.session_state.exam_opec_number = None
    st.session_state.exam_marked_questions = []
    st.session_state.pop("exam_simulation_policy_version", None)
    st.session_state.pop("exam_blueprint_version", None)
    st.session_state.pop("exam_minutes_per_question", None)
    st.session_state.pop("exam_navigation_mode", None)
    st.session_state.pop("exam_target_questions", None)
    st.session_state.pop("exam_evidence_session_id", None)
    st.session_state.pop("exam_evidence_warning", None)
    if clear_review:
        st.session_state.last_exam_cases = []
        st.session_state.last_user_answers = {}
        st.session_state.pop("exam_score", None)
        st.session_state.pop("show_simulacro_analisis", None)


def _sanitize_exam_session_state():
    db = next(get_db())
    try:
        competition_id, opec_number = _active_opec_scope(
            db, st.session_state.get("user_id")
        )
        eligible_question_ids = _eligible_question_ids(
            db,
            st.session_state.get("user_id"),
            competition_id,
            opec_number,
            partition="measurement",
        ) if competition_id and opec_number else set()
    finally:
        db.close()

    active_cases = st.session_state.get("exam_cases", []) or []
    review_cases = st.session_state.get("last_exam_cases", []) or []
    has_exam_state = bool(
        st.session_state.get("exam_active")
        or active_cases
        or review_cases
        or st.session_state.get("exam_score")
    )
    same_context = _same_exam_context(
        st.session_state.get("exam_competition_id"),
        st.session_state.get("exam_opec_number"),
        competition_id,
        opec_number,
    )
    if has_exam_state and not same_context:
        _reset_invalid_exam_state(clear_review=True)
        return

    if st.session_state.get("exam_active") and not active_cases:
        _reset_invalid_exam_state(clear_review=True)
        return

    if active_cases and not all(
        getattr(case, "competition_id", None) == competition_id
        and _case_is_valid_for_opec(case, opec_number, eligible_question_ids)
        for case in active_cases
    ):
        _reset_invalid_exam_state(clear_review=True)
        return

    if review_cases and not all(
        getattr(case, "competition_id", None) == competition_id
        and _case_is_valid_for_opec(case, opec_number, eligible_question_ids)
        for case in review_cases
    ):
        _reset_invalid_exam_state(clear_review=True)


_sanitize_exam_session_state()


def load_exam_cases():
    db = next(get_db())
    user_id = st.session_state.get("user_id")

    try:
        competition_id, opec_number = _active_opec_scope(db, user_id)
        if competition_id is None or not opec_number:
            return [], None, None, None, None
        query = db.query(CaseStudy).options(joinedload(CaseStudy.questions))
        query = query.filter(CaseStudy.competition_id == competition_id)

        measurement_ids = _eligible_question_ids(
            db,
            user_id,
            competition_id,
            opec_number,
            partition="measurement",
        )
        blocks = _reviewed_blocks_for_opec(
            query.all(), opec_number, measurement_ids
        )
        if not blocks:
            return [], competition_id, opec_number, None, None

        # Prefer weak topics, while preserving balanced coverage by domain.
        smart_topics = StatsService.get_smart_mix_topics(
            user_id, count=2, competition_id=competition_id
        ) if user_id else []
        _, blueprint, policy = _policy_blueprint(
            db,
            competition_id,
            opec_number,
            reviewed_case_count=len(blocks),
        )
        prior_events = []
        if _phase2_evidence_available(db):
            prior_events = (
                db.query(OpecLearningEvent)
                .join(
                    OpecLearningSession,
                    OpecLearningEvent.session_id == OpecLearningSession.id,
                )
                .filter(
                    OpecLearningEvent.user_id == user_id,
                    OpecLearningSession.competition_id == competition_id,
                    OpecLearningSession.opec_number == str(opec_number),
                    OpecLearningSession.mode == "measurement",
                    OpecLearningSession.bank_partition == "measurement",
                    OpecLearningSession.status == "completed",
                )
                .all()
            )
        selection = select_novel_measurement_blocks(
            blocks,
            target_count=blueprint.target_cases,
            snapshot=exposure_snapshot(prior_events),
            preferred_topics=smart_topics,
        )
        st.session_state["measurement_selection_reason"] = selection.reason
        st.session_state["measurement_novel_available"] = selection.novel_available
        st.session_state["measurement_target_cases"] = selection.requested_count
        if not selection.complete:
            return [], competition_id, opec_number, policy, blueprint
        selected_blocks = list(selection.blocks)
        selected_question_count = sum(
            len(getattr(block, "questions", None) or ())
            for block in selected_blocks
        )
        if selected_question_count != blueprint.target_questions:
            st.session_state["measurement_selection_reason"] = (
                f"La política solicita {blueprint.target_questions} preguntas, pero los "
                f"casos nuevos seleccionados reúnen {selected_question_count}. Amplía o "
                "reorganiza la partición de medición sin dividir casos PJS."
            )
            return [], competition_id, opec_number, policy, blueprint
        return selected_blocks, competition_id, opec_number, policy, blueprint
    except SimulationPolicyValidationError as exc:
        st.session_state["measurement_selection_reason"] = (
            f"La política de simulacro no es válida: {exc}"
        )
        return [], None, None, None, None
    except Exception as exc:
        log_ui_exception("measurement.blocks.load", exc)
        return [], None, None, None, None
    finally:
        db.close()

def start_exam():
    with st.spinner("Preparando entorno de examen..."):
        cases, competition_id, opec_number, policy, blueprint = load_exam_cases()
        if not cases:
            st.error(
                st.session_state.get(
                    "measurement_selection_reason",
                    "No hay suficientes casos situacionales revisados y nuevos para esta medición.",
                )
            )
            return
        if policy is None or blueprint is None:
            st.error("No se pudo resolver la política versionada de esta OPEC.")
            return
        
        st.session_state.exam_cases = cases
        st.session_state.exam_active = True
        st.session_state.exam_start_time = datetime.datetime.now()
        st.session_state.current_case_idx = 0
        st.session_state.user_answers = {}
        st.session_state.exam_marked_questions = []
        st.session_state.exam_competition_id = competition_id
        st.session_state.exam_opec_number = opec_number
        st.session_state.exam_simulation_policy_version = policy.policy_version
        st.session_state.exam_blueprint_version = (
            f"{policy.policy_version}:full:q{blueprint.target_questions}:"
            f"m{blueprint.minutes_per_question:g}:nav-{blueprint.navigation_mode}"
        )
        st.session_state.exam_minutes_per_question = blueprint.minutes_per_question
        st.session_state.exam_navigation_mode = blueprint.navigation_mode
        st.session_state.exam_target_questions = blueprint.target_questions
        st.session_state.pop("exam_evidence_session_id", None)
        st.session_state.pop("exam_evidence_warning", None)
        st.rerun()

def finish_exam():
    """Persist one strict measurement with no inferred confidence or time."""
    correct = 0
    total = 0
    user_id = st.session_state.get("user_id")
    exam_competition_id = st.session_state.get("exam_competition_id")
    exam_opec_number = st.session_state.get("exam_opec_number")
    exam_cases = list(st.session_state.get("exam_cases", []) or [])
    db = next(get_db())
    try:
        measurement_ids = _eligible_question_ids(
            db,
            user_id,
            exam_competition_id,
            exam_opec_number,
            partition="measurement",
        )
        if not exam_cases or not all(
            getattr(case, "competition_id", None) == exam_competition_id
            and _case_is_valid_for_opec(case, exam_opec_number, measurement_ids)
            for case in exam_cases
        ):
            raise ValueError("El contexto del simulacro cambió durante la sesión.")

        ordered_question_ids = [
            str(question.question_id)
            for case in exam_cases
            for question in case.questions
        ]
        fresh_questions = db.query(Question).filter(
            Question.question_id.in_(ordered_question_ids)
        ).all()
        by_id = {str(question.question_id): question for question in fresh_questions}
        if set(ordered_question_ids) != set(by_id):
            raise ValueError("Una pregunta de la medición ya no está disponible.")
        active_opec = db.query(UserOPEC).filter_by(
            user_id=user_id, is_active=True
        ).first()
        if active_opec is None or str(active_opec.opec_number) != str(exam_opec_number):
            raise ValueError("La OPEC activa ya no coincide con la medición.")
        _, current_simulation_policy = _simulation_policy_for_scope(
            db,
            exam_competition_id,
            exam_opec_number,
        )
        stored_simulation_policy_version = str(
            st.session_state.get("exam_simulation_policy_version") or ""
        )
        if current_simulation_policy.policy_version != stored_simulation_policy_version:
            raise ValueError(
                "La política de simulacro cambió durante la sesión; el resultado no es comparable."
            )

        evidence_session = None
        if _phase2_evidence_available(db):
            evidence_session = start_opec_session(
                db,
                user_id=user_id,
                questions=[by_id[question_id] for question_id in ordered_question_ids],
                mode="measurement",
                bank_partition="measurement",
                competition_id=exam_competition_id,
                user_opec_id=active_opec.id,
                policy_version=ReadinessPolicy().version,
                blueprint_version=st.session_state.get("exam_blueprint_version"),
                feedback_enabled=False,
                aids_used=False,
                now=st.session_state.exam_start_time,
            )

        item_results = []
        for question_id in ordered_question_ids:
            question = by_id[question_id]
            user_choice = st.session_state.user_answers.get(question.question_id)
            is_correct = user_choice == question.correct_key
            correct += int(is_correct)
            total += 1
            if evidence_session is not None:
                event_row = record_opec_event(
                    db,
                    session_id=evidence_session.id,
                    user_id=user_id,
                    question_id=question_id,
                    chosen_key=user_choice if user_choice else "SKIPPED",
                    confidence=None,
                    time_sec=None,
                )
                item_results.append({
                    "question_id": question_id,
                    "revision_id": event_row.question_revision_id,
                    "case_id": event_row.case_id,
                    "function_number": event_row.function_number,
                    "is_correct": event_row.is_correct,
                    "track": question.track,
                    "question_type": question.question_type,
                })

        if evidence_session is not None:
            finalize_opec_session(
                db,
                session_id=evidence_session.id,
                user_id=user_id,
                require_complete=True,
            )
            st.session_state.exam_evidence_session_id = evidence_session.id
            st.session_state.pop("exam_evidence_warning", None)
        else:
            st.session_state.exam_evidence_warning = (
                "La medición se completó, pero falta aplicar la migración de evidencia Fase 2."
            )

        completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        started_at = st.session_state.exam_start_time
        duration_seconds = max(
            0,
            int((completed_at - started_at).total_seconds())
            if isinstance(started_at, datetime.datetime) else 0,
        )
        result_payload = {
            "session_kind": "measurement",
            "mode": "measurement",
            "competition_id": exam_competition_id,
            "opec_number": str(exam_opec_number),
            "evidence_session_id": evidence_session.id if evidence_session else None,
            "policy_version": evidence_session.policy_version if evidence_session else None,
            "blueprint_version": evidence_session.blueprint_version if evidence_session else None,
            "simulation_policy_version": stored_simulation_policy_version,
            "bank_partition": "measurement",
            "completed": True,
            "feedback_enabled": False,
            "aids_used": False,
            "total": total,
            "correct": correct,
            "score": (correct / total * 100.0) if total else 0.0,
            "functional_score": (correct / total * 100.0) if total else None,
            "duration_seconds": duration_seconds,
            "q_ids": ordered_question_ids,
            "question_revision_ids": (
                list(evidence_session.question_revision_ids or []) if evidence_session else []
            ),
            "case_ids": list(evidence_session.case_ids or []) if evidence_session else [],
            "coverage": dict(evidence_session.coverage or {}) if evidence_session else {},
            "items": item_results,
            "marked_for_review": list(
                dict.fromkeys(st.session_state.get("exam_marked_questions", []))
            ),
            "completed_at": completed_at.isoformat(),
        }
        save_last_result(
            db,
            user_id,
            result_payload,
            competition_id=exam_competition_id,
            opec_number=str(exam_opec_number),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _reset_invalid_exam_state(clear_review=True)
        log_ui_exception("measurement.evidence.save", exc)
        st.error("La medición no pudo guardarse de forma segura. Intenta nuevamente.")
        st.rerun()
    finally:
        db.close()

    # Keep legacy points/history compatible, but never fabricate missing time.
    for question_id in ordered_question_ids:
        question = by_id[question_id]
        user_choice = st.session_state.user_answers.get(question.question_id)
        try:
            StatsService.record_attempt(
                user_id=user_id,
                question_id=question.question_id,
                chosen_key=user_choice if user_choice else "SKIPPED",
                is_correct=user_choice == question.correct_key,
                time_sec=None,
            )
        except Exception as exc:
            log_ui_exception("measurement.legacy_stats", exc)

    st.session_state.exam_score = (correct, total)
    # Save for review
    st.session_state.last_exam_cases = st.session_state.exam_cases
    st.session_state.last_user_answers = st.session_state.user_answers
    
    st.session_state.exam_active = False
    st.rerun()

# --- VISTA PRINCIPAL ---

if not st.session_state.exam_active:
    # --- PANTALLA DE INICIO CON PROTOCOLO ---
    reviewed_cases, review_cases, novel_cases = _reviewed_inventory()
    try:
        _active_competition, exam_blueprint, simulation_policy = _active_exam_context(
            reviewed_cases
        )
    except SimulationPolicyValidationError as exc:
        st.error(f"La política de simulacro de esta OPEC requiere corrección: {exc}")
        st.stop()
    if exam_blueprint is None or simulation_policy is None:
        st.warning("Activa una OPEC antes de preparar una medición.")
        st.stop()

    navigation_labels = {
        "sequential": "Secuencial; no se regresa a casos cerrados",
        "case_locked": "El caso se responde y se cierra como bloque",
        "free": "Libre entre casos mientras quede tiempo",
    }
    st.markdown(f"""
    ### 🎯 Sobre esta práctica PJS
    Este modo mide tu desempeño sin retroalimentación ni ayudas durante la sesión.

    * **Formato:** caso situacional con hasta {exam_blueprint.questions_per_case} preguntas relacionadas
    * **Tiempo interno:** {exam_blueprint.minutes_per_question:g} minutos por pregunta
    * **Navegación:** {navigation_labels.get(exam_blueprint.navigation_mode, exam_blueprint.navigation_mode)}
    * **Resultado:** se revela únicamente al finalizar

    La cantidad y la duración son parámetros internos editables; no son cifras oficiales
    del cuadernillo mientras la CNSC no publique esos datos para el proceso.
    """)

    st.title(f"⏱️ {exam_blueprint.title}")
    target_cases = exam_blueprint.target_cases
    inventory_cols = st.columns(4)
    inventory_cols[0].metric("Casos aptos para medición", reviewed_cases)
    inventory_cols[1].metric("Casos nuevos para ti", novel_cases)
    inventory_cols[2].metric("Meta interna", f"{exam_blueprint.target_questions} preguntas")
    inventory_cols[3].metric("Casos candidatos", review_cases)
    st.progress(min(reviewed_cases / target_cases, 1.0))
    st.markdown(
        f"**Plan interno versionado:** {target_cases} casos · "
        f"{exam_blueprint.target_questions} preguntas · "
        f"{exam_blueprint.target_minutes} minutos · "
        f"versión `{simulation_policy.policy_version}`."
    )
    if simulation_policy.official.question_count is None:
        st.caption(
            "Cantidad y duración oficiales: pendientes de publicación. La evidencia "
            "oficial disponible sustenta la metodología PJS, no esos dos parámetros."
        )
    if reviewed_cases < 2:
        st.warning(
            "El banco de medición aún no tiene suficientes casos con fuente oficial "
            "verificada individualmente. El material provisional permanece en práctica "
            "y no se presenta como examen validado."
        )
    elif novel_cases < target_cases:
        st.warning(
            f"Solo quedan {novel_cases} casos no vistos y esta configuración solicita "
            f"{target_cases}. La medición queda bloqueada para no reutilizar material "
            "y aparentar evidencia comparable."
        )
    if "exam_score" in st.session_state:
        c, t = st.session_state.exam_score
        pct = (c/t)*100 if t > 0 else 0
        st.success(f"### Resultado Final: {c}/{t} ({pct:.1f}%)")
        st.markdown("### Resumen de sesión")
        st.caption(f"Correctas: {c} de {t} preguntas | Puntaje: {pct:.1f}%")
        marked_count = len(st.session_state.get("exam_marked_questions", []))
        if marked_count:
            st.caption(f"Marcaste {marked_count} pregunta(s) para revisión posterior.")
        if st.session_state.get("exam_evidence_warning"):
            st.warning(st.session_state["exam_evidence_warning"])
        elif st.session_state.get("exam_evidence_session_id"):
            readiness_db = next(get_db())
            try:
                active_opec = readiness_db.query(UserOPEC).filter_by(
                    user_id=st.session_state.get("user_id"), is_active=True
                ).first()
                plan = (
                    readiness_db.query(OpecStudyPlan).filter_by(
                        user_id=st.session_state.get("user_id"),
                        competition_id=active_opec.competition_id,
                        user_opec_id=active_opec.id,
                    ).first()
                    if active_opec else None
                )
                policy = ReadinessPolicy(
                    target_score=float(plan.target_score if plan else 85.0)
                )
                assessment = evaluate_opec_readiness(
                    readiness_db,
                    user_id=st.session_state.get("user_id"),
                    user_opec_id=active_opec.id if active_opec else None,
                    policy=policy,
                )
                st.markdown("### Evidencia hacia tu meta")
                readiness_cols = st.columns(2)
                readiness_cols[0].metric(
                    "Objetivo interno de precisión",
                    f"{assessment.target_score:.0f}%",
                )
                readiness_cols[1].metric(
                    "Repetición válida",
                    assessment.repeated_target_label.replace("meta interna repetida ", ""),
                )
                if assessment.internal_precision_goal_met:
                    st.success(
                        "Cumpliste la meta interna repetida en mediciones comparables. "
                        "La retención diferida se evalúa por separado."
                    )
                else:
                    next_reasons = list(assessment.reasons[:3])
                    st.info(
                        "Esta sesión suma evidencia, pero todavía no abre la puerta interna de preparación."
                    )
                    if next_reasons:
                        st.markdown("**Qué falta:**\n" + "\n".join(
                            f"- {reason}" for reason in next_reasons
                        ))
                st.caption(
                    f"El {assessment.official_functional_minimum_score:.0f}/100 es el mínimo "
                    "oficial de la prueba funcional DIAN 2676; esta pantalla no calcula un "
                    "resultado oficial ni una probabilidad de obtener el empleo."
                )
            except Exception as exc:
                log_ui_exception("measurement.readiness_summary", exc)
                st.caption("La evidencia se guardó; el resumen de preparación no pudo cargarse.")
            finally:
                readiness_db.close()
        
        wrong_count = t - c
        st.markdown(f"**Errores:** {wrong_count}")
        if wrong_count == 0:
            st.success("¡Excelente. No hay fallos detectables en este intento.")
        
        if st.button("Ver análisis detallado y recomendaciones", use_container_width=True):
            st.session_state["show_simulacro_analisis"] = True
            st.rerun()
        
        if not st.session_state.get("show_simulacro_analisis", False):
            st.markdown("Puedes continuar al siguiente simulacro y revisar después las áreas de mejora.")
        else:
            st.markdown("### 🧠 Análisis y recomendaciones")
            # --- RECOMENDACIONES DE ESTUDIO DETALLADAS (v7.0) ---
            cases = st.session_state.get("last_exam_cases", [])
            answers = st.session_state.get("last_user_answers", {})
            
            failed_details = {}  # {topic_key: {...}}
            
            for c_idx, case in enumerate(cases):
                if not _case_is_valid_for_opec(
                    case, st.session_state.get("exam_opec_number")
                ):
                    continue
                for q in case.questions:
                    user_ans = answers.get(q.question_id)
                    if user_ans == q.correct_key:
                        continue
                    # Determinar el tema/micro-competencia más específico
                    topic_name = q.micro_competencia or q.competency or q.topic or "Competencia General"
                    if topic_name.upper().startswith("OPEC") and "-" in topic_name:
                        topic_name = topic_name.split("-")[-1].strip()
                    
                    track_name = q.track or "FUNCIONAL"
                    macro_name = q.macro_dominio or "General"
                    
                    if topic_name not in failed_details:
                        failed_details[topic_name] = {
                            "topic": topic_name,
                            "track": track_name,
                            "macro": macro_name,
                            "refs": set(),
                            "questions": []
                        }
                    
                    # Agregar referencias limpias
                    ref = getattr(q, 'source_refs', None)
                    if ref:
                        ref_str = str(ref).strip()
                        if ref_str.upper() not in ["", "IA", "NONE", "NULL"]:
                            rf_upper = ref_str.upper()
                            if not ("MISTRAL" in rf_upper or "BATCH GEN" in rf_upper or "INICIAL DIAN" in rf_upper):
                                for r in ref_str.split('\n'):
                                    if r.strip():
                                        failed_details[topic_name]["refs"].add(r.strip())
                    # Agregar detalles de la pregunta fallada
                    failed_details[topic_name]["questions"].append({
                        "stem": q.stem,
                        "chosen": user_ans,
                        "correct": q.correct_key,
                        "correct_text": q.options_json.get(q.correct_key) if q.options_json else "",
                        "rationale": q.rationale
                    })
            
            for t_name, detail in failed_details.items():
                track_val = detail["track"].upper()
                track_color = "#E60000" if "FUNCIONAL" in track_val else "#3b82f6" if "COMPORTAMENTAL" in track_val else "#10b981"
                refs_list = list(detail["refs"])
                
                st.markdown(f"**{detail['topic']}** — {detail['macro']} ({detail['track']})")
                if refs_list:
                    st.caption("Fuentes sugeridas: " + " | ".join(refs_list[:3]))
                for q_item in detail["questions"]:
                    stem_display = q_item["stem"]
                    if "PREGUNTA:" in stem_display:
                        try:
                            stem_display = stem_display.split("PREGUNTA:")[1].strip()
                        except (IndexError, AttributeError):
                            pass
                    st.markdown(f"- Tú: `{q_item['chosen']}` | Correcta: `{q_item['correct']}`")
                    if q_item["rationale"]:
                        st.caption(q_item["rationale"])
                if st.button(f"Practicar tema '{t_name}'", key=f"reforce_{t_name}", use_container_width=True):
                    st.session_state["practice_recommended_topic"] = t_name
                    st.switch_page("pages/1_Nuevo_Simulacro.py")
            
            if st.button("Ocultar análisis detallado", use_container_width=True):
                st.session_state["show_simulacro_analisis"] = False
                st.rerun()
    
    if st.button(
        "🔴 INICIAR PRÁCTICA CRONOMETRADA",
        type="primary",
        use_container_width=True,
        disabled=reviewed_cases == 0 or novel_cases < target_cases,
    ):
        # Clear previous review data
        if "last_exam_cases" in st.session_state:
            del st.session_state.last_exam_cases
        if "last_user_answers" in st.session_state:
            del st.session_state.last_user_answers
        if "exam_score" in st.session_state:
            del st.session_state.exam_score
        if "show_simulacro_analisis" in st.session_state:
            del st.session_state.show_simulacro_analisis
        start_exam()

else:
    # --- SESIÓN PJS CRONOMETRADA ---
    
    # 1. Timer Logic
    elapsed = datetime.datetime.now() - st.session_state.exam_start_time
    total_questions = sum(len(c.questions) for c in st.session_state.exam_cases)
    # Parámetro interno editable hasta que la GOA DIAN 2676 publique la duración.
    total_time_min = total_questions * float(
        st.session_state.get("exam_minutes_per_question", 2.0)
    )
    remaining = datetime.timedelta(minutes=total_time_min) - elapsed
    
    if remaining.total_seconds() <= 0:
        st.warning("¡TIEMPO TERMINADO!")
        finish_exam()
    
    # Render Timer
    mins, secs = divmod(int(remaining.total_seconds()), 60)
    time_left_secs = max(0, int(remaining.total_seconds()))
    color = "#e74c3c" if time_left_secs < 60 else "#2e86c1"
    st.markdown(f"""
    <div class="timer-box" id="timer-box-real" style="background-color: {color};">
        <span id="countdown-real">{mins:02d}:{secs:02d}</span>
    </div>
    """, unsafe_allow_html=True)
    
    js_code = f"""
    <script>
    (function() {{
        let secondsLeft = {time_left_secs};
        const parentDoc = window.parent.document;
        
        function clickStreamlitButton(labelText) {{
            const buttons = Array.from(parentDoc.querySelectorAll("button"));
            for (const btn of buttons) {{
                if (btn.innerText && btn.innerText.toUpperCase().includes(labelText.toUpperCase())) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}
        
        if (window.parent.examRealTimerInterval) {{
            clearInterval(window.parent.examRealTimerInterval);
        }}
        
        window.parent.examRealTimerInterval = setInterval(() => {{
            secondsLeft--;
            if (secondsLeft <= 0) {{
                clearInterval(window.parent.examRealTimerInterval);
                const cd = parentDoc.getElementById("countdown-real");
                if (cd) cd.innerText = "00:00";
                
                // Tratar de finalizar el examen o pasar al siguiente caso (lo cual forzará el fin del examen en backend)
                if (!clickStreamlitButton("FINALIZAR PRÁCTICA")) {{
                    clickStreamlitButton("Siguiente Caso");
                }}
            }} else {{
                const cd = parentDoc.getElementById("countdown-real");
                if (cd) {{
                    const m = Math.floor(secondsLeft / 60);
                    const s = secondsLeft % 60;
                    cd.innerText = (m < 10 ? '0' : '') + m + ":" + (s < 10 ? '0' : '') + s;
                }}
                const box = parentDoc.getElementById("timer-box-real");
                if (secondsLeft < 60) {{
                    if (box) box.style.backgroundColor = "#e74c3c";
                }} else {{
                    if (box) box.style.backgroundColor = "#2e86c1";
                }}
            }}
        }}, 1000);
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)
    
    # 2. Global Progress
    current_idx = st.session_state.current_case_idx
    current_case = st.session_state.exam_cases[current_idx]

    if not _case_is_valid_for_opec(
        current_case, st.session_state.get("exam_opec_number")
    ):
        _reset_invalid_exam_state(clear_review=True)
        st.warning("Se detecto un caso invalido y fue descartado antes de mostrarlo.")
        st.rerun()
    
    st.markdown(f"<div style='font-weight:700; margin-bottom:0.8rem; color:#475569;'>Caso {current_idx + 1} de {len(st.session_state.exam_cases)}</div>", unsafe_allow_html=True)
    
    # 3. Layout: One flow (text + questions + one action)
    st.markdown(f"### 📄 {current_case.title or 'Situación'}")
    st.markdown(f'<div class="case-text">{escape_html(current_case.text)}</div>', unsafe_allow_html=True)

    st.markdown("### ❓ Preguntas del Caso")
    for i, q in enumerate(current_case.questions):
        st.markdown(f"#### Pregunta {i+1}")
        st.write(q.stem)

        opts = q.options_json
        options_list = list(opts.keys())

        # Key for state
        k = f"q_{q.question_id}"

        prev_sel = st.session_state.user_answers.get(q.question_id)
        idx = options_list.index(prev_sel) if prev_sel in options_list else None

        sel = st.radio(
            "Seleccione una opción:",
            options_list,
            format_func=lambda x: f"{x}) {opts[x]}",
            key=k,
            index=idx,
            label_visibility="collapsed"
        )

        if sel:
            st.session_state.user_answers[q.question_id] = sel
        marked_ids = set(st.session_state.get("exam_marked_questions", []))
        marked = st.checkbox(
            "🔖 Marcar para revisión",
            value=str(q.question_id) in marked_ids,
            key=f"exam_mark_{q.question_id}",
        )
        if marked:
            marked_ids.add(str(q.question_id))
        else:
            marked_ids.discard(str(q.question_id))
        st.session_state.exam_marked_questions = sorted(marked_ids)

    is_last = current_idx == len(st.session_state.exam_cases) - 1
    navigation_mode = st.session_state.get("exam_navigation_mode", "sequential")
    if navigation_mode == "free" and current_idx > 0:
        previous_col, next_col = st.columns(2)
        if previous_col.button("⬅️ Caso anterior", use_container_width=True):
            st.session_state.current_case_idx -= 1
            st.rerun()
        advance = next_col.button(
            "Siguiente Caso ➡️" if not is_last else "FINALIZAR PRÁCTICA 🏁",
            type="primary",
            use_container_width=True,
        )
    else:
        advance = st.button(
            "Siguiente Caso ➡️" if not is_last else "FINALIZAR PRÁCTICA 🏁",
            type="primary",
            use_container_width=True,
        )
    if advance:
        if is_last:
            finish_exam()
        else:
            st.session_state.current_case_idx += 1
            st.rerun()

