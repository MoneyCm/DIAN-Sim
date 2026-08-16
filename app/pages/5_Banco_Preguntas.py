import streamlit as st
import pandas as pd
import os, sys, uuid, datetime, io, time, importlib
from collections import Counter
from sqlalchemy import inspect as sqlalchemy_inspect

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import OpecProfile, Question, QuestionOpecScope, UserOPEC
from core.dedupe import compute_hash, find_duplicates
from core.import_utils import validate_import_df
from core.generators import llm as llm_module
if getattr(llm_module, "LLM_AUDIT_RUNTIME_VERSION", None) != "safe-fallback-v2":
    llm_module = importlib.reload(llm_module)
LLMGenerator = llm_module.LLMGenerator
from core.config import get_api_key
from ui_utils import load_css, log_ui_exception, render_header

from core.auth import AuthManager
from core.bank_partition import (
    BANK_PARTITIONS,
    MAX_PARTITION_BATCH,
    BankPartitionError,
    list_partition_items,
    move_question_partitions,
    partition_counts,
    partition_schema_available,
    resolve_active_bank_context,
)
from core.competitions import get_active_competition_id
from core.exam_format import (
    OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL, question_format_status,
)
from core.legacy_question_audit import is_safe_for_active_study
from core.question_opec_scope import stamp_question_opec
from core.question_review import (
    COGNITIVE_LEVELS, QUALITY_ALL, QUALITY_PENDING, QUALITY_REINFORCEMENTS, QUALITY_VERIFIED,
    approve_candidate, candidate_validation_error, is_reinforcement_candidate,
    matches_quality_filter, record_ai_audit, record_editorial_verification,
    reject_candidate,
)
from core.learning.engine import editorial_question_difficulty
from core.opec_question_context import function_number_for_question

try:
    from core.question_review import is_pending_review_candidate
except ImportError:
    # Streamlit can briefly retain an older core module while the page has
    # already been reloaded. Keep the bank available during that transition.
    def is_pending_review_candidate(question):
        return is_reinforcement_candidate(question)

def automatic_rejection_reason(question):
    """Classify only content that is unsafe to retain as active study material.

    Kept on the page so a Cloud worker that still holds an older core module
    cannot make the review screen use an outdated source rule.
    """
    report = getattr(question, "quality_report", None)
    report = report if isinstance(report, dict) else {}
    audit = report.get("ai_audit")
    status = str(audit.get("status", "")).strip().upper() if isinstance(audit, dict) else ""
    source = str(getattr(question, "source_refs", "") or "").strip().lower()
    generated_source = (
        not source
        or "batch gen" in source
        or "banco base provisional" in source
        or "guía oficial pendiente" in source
        or "guia oficial pendiente" in source
        or "inyección especial" in source
        or "inyeccion especial" in source
        or "antigravity" in source
        or source.startswith(("mistral -", "openai -", "gemini -"))
    )
    if status == "REJECTED":
        return "Dictamen IA de rechazo; requiere reescritura o nueva fuente oficial."
    if assess_source_evidence(question)["status"] == "UNTRACEABLE":
        return "No contiene fuente oficial directa ni ancla normativa reconocible."
    if generated_source:
        return "Fuente generada o provisional, sin trazabilidad oficial verificable."
    return None


def needs_ai_audit(question):
    """Audit new candidates and retry only audits that ended in a technical error."""
    report = getattr(question, "quality_report", None)
    audit = report.get("ai_audit") if isinstance(report, dict) else None
    if not isinstance(audit, dict):
        return True
    return str(audit.get("status", "")).strip().upper() == "ERROR"

from core.question_quality import audit_bank, audit_question_structure, store_deterministic_audit

try:
    from core import source_evidence as source_evidence_module
    if getattr(source_evidence_module, "SOURCE_EVIDENCE_VERSION", None) != "official-links-v3":
        source_evidence_module = importlib.reload(source_evidence_module)
    assess_source_evidence = source_evidence_module.assess_source_evidence
    has_precise_source_verification = source_evidence_module.has_precise_source_verification
    precise_source_verification_error = source_evidence_module.precise_source_verification_error
except Exception:
    def assess_source_evidence(question):
        source = str(getattr(question, "source_refs", "") or "").strip()
        return {
            "status": "SOURCE_CHECK_UNAVAILABLE" if source else "UNTRACEABLE",
            "article": None,
            "official_url": "",
            "reason": "La comprobación de fuente se está actualizando.",
        }

    def has_precise_source_verification(question):
        return False

    def precise_source_verification_error(question):
        return "La comprobación normativa individual no está disponible."

QUALITY_LOCAL_REVIEW = "Diagnóstico local: revisar 🔬"

AI_AUDIT_RESULT_VERSION = "v2"
GEMINI_AUDIT_REQUEST_DELAY_SECONDS = 6


def retain_allowed_questions(questions, allowed_question_ids):
    """Keep bulk actions inside the OPEC inventory shown to the user."""
    allowed = {str(value) for value in allowed_question_ids}
    return [
        question for question in questions
        if str(getattr(question, "question_id", "")) in allowed
    ]


def retain_training_partition(db, questions, active_opec):
    """Exclude measurement, anchor and reserved items from study-facing views."""
    if active_opec is None:
        return []
    try:
        inspector = sqlalchemy_inspect(db.connection())
        required = {OpecProfile.__tablename__, QuestionOpecScope.__tablename__}
        if not required.issubset(set(inspector.get_table_names())):
            return list(questions)
    except (AttributeError, TypeError):
        return list(questions)

    profile = db.query(OpecProfile).filter_by(
        competition_id=active_opec.competition_id,
        opec_number=str(active_opec.opec_number),
    ).first()
    if profile is None:
        return list(questions)
    training_ids = {
        str(row[0])
        for row in db.query(QuestionOpecScope.question_id).filter(
            QuestionOpecScope.opec_profile_id == profile.id,
            QuestionOpecScope.bank_partition == "training",
        ).all()
    }
    return retain_allowed_questions(questions, training_ids)


def assign_question_to_opec(db, question, active_opec):
    """Record legacy metadata and canonical scope when that schema exists."""
    if active_opec is None:
        raise ValueError("Activa una OPEC antes de crear o importar preguntas.")
    stamp_question_opec(question, active_opec.opec_number)
    try:
        inspector = sqlalchemy_inspect(db.connection())
        required = {OpecProfile.__tablename__, QuestionOpecScope.__tablename__}
        if not required.issubset(set(inspector.get_table_names())):
            return
    except (AttributeError, TypeError):
        return

    profile = db.query(OpecProfile).filter_by(
        competition_id=active_opec.competition_id,
        opec_number=str(active_opec.opec_number),
    ).first()
    if profile is not None:
        db.add(QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=profile.id,
            scope_kind="primary",
            bank_partition="training",
        ))


def queue_item(question):
    report = getattr(question, "quality_report", None)
    if isinstance(report, dict) and report.get("origin") in {
        "reinforcement_candidate", "progressive_opec_local", "manual_question_review",
    }:
        return True
    return not bool(getattr(question, "is_verified", False)) and bool(
        str(getattr(question, "source_refs", "") or "").strip()
    ) and not (isinstance(report, dict) and report.get("status") == "REJECTED")


def queue_summary(questions):
    items = [question for question in questions if queue_item(question)]
    pending = [question for question in items if not bool(getattr(question, "is_verified", False))
               and (getattr(question, "quality_report", None) or {}).get("status") != "REJECTED"]
    statuses = [(getattr(question, "quality_report", None) or {}).get("status") for question in items]
    return {
        "total": len(items), "pending": len(pending),
        "approved": statuses.count("APPROVED"), "rejected": statuses.count("REJECTED"),
        "next_question": min(pending, key=lambda item: str(item.question_id), default=None),
    }


def queue_validation_error(question, peers=()):
    error = candidate_validation_error(question)
    if error:
        return error
    other_stems = [
        str(getattr(peer, "stem", "") or "")
        for peer in peers or ()
        if str(getattr(peer, "question_id", ""))
        != str(getattr(question, "question_id", ""))
    ]
    if find_duplicates(str(getattr(question, "stem", "") or ""), other_stems, threshold=92):
        return "Existe una pregunta demasiado similar; revisa el posible duplicado antes de aprobar."
    return None


def save_queue_decision(question, reviewer, approved, reason=""):
    if approved:
        approve_candidate(question, reviewer)
    else:
        reject_candidate(question, reviewer, reason)


def quality_state(question):
    """Classify bank readiness without letting an AI opinion certify content."""
    if (
        bool(getattr(question, "is_verified", False))
        and has_precise_source_verification(question)
    ):
        return (
            "LISTA PARA ESTUDIAR",
            "Tiene revisión y evidencia normativa individual completas.",
            None,
        )

    rejection_reason = automatic_rejection_reason(question)
    if rejection_reason:
        return "NO USAR", rejection_reason, None

    source = assess_source_evidence(question)
    structural = audit_question_structure(question)
    if source["status"] != "DIRECT_OFFICIAL_SOURCE":
        return "SIN EVIDENCIA OFICIAL", source["reason"], source
    if structural["status"] != "PASS":
        return "CORREGIR ESTRUCTURA", "El diagnóstico automático encontró campos por corregir.", source
    precise_error = precise_source_verification_error(question)
    return (
        "EN CONTRASTE NORMATIVO",
        precise_error
        or "Falta registrar la decisión editorial individual antes de habilitarla.",
        source,
    )

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="Banco de preguntas", subtitle="Consulta, calidad y cobertura del concurso activo")

# --- INITIALIZATION ---
if "bulk_selection" not in st.session_state:
    st.session_state["bulk_selection"] = set()
if "page_num" not in st.session_state:
    st.session_state["page_num"] = 1

def reset_selection():
    st.session_state["bulk_selection"] = set()
    # Clear individual checkbox keys Mikey v36
    for key in list(st.session_state.keys()):
        if key.startswith("sel_"):
            st.session_state[key] = False

def reset_pagination():
    st.session_state["page_num"] = 1


is_admin_user = AuthManager.is_admin()
available_actions = ["Consultar banco"]
if is_admin_user:
    available_actions.extend(
        [
            "Centro de calidad",
            "Particiones del banco",
            "Importar archivo",
            "Crear manualmente",
        ]
    )
if st.session_state.get("Vista") == "Revisión guiada":
    st.session_state["Vista"] = "Centro de calidad"
action = st.selectbox("Vista", available_actions, label_visibility="collapsed", key="Vista")
st.divider()

db = SessionLocal()

if not is_admin_user:
    st.info("Modo consulta: solo los administradores pueden crear, auditar o eliminar preguntas.")

u_id = st.session_state.get("user_id")
from services.question_service import QuestionService

# El concurso no identifica por sí solo un cargo. Toda esta página usa un
# inventario único, previamente aislado por la OPEC activa.
active_opec = (
    db.query(UserOPEC)
    .filter_by(user_id=u_id, is_active=True)
    .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
    .first()
)
competition_id = (
    active_opec.competition_id
    if active_opec is not None
    else get_active_competition_id(db, u_id)
)
active_opec_number = (
    str(active_opec.opec_number).strip()
    if active_opec is not None and active_opec.opec_number
    else ""
)
bank_context_key = f"{competition_id or 'none'}:{active_opec_number or 'none'}"
if st.session_state.get("bank_opec_context") != bank_context_key:
    reset_selection()
    reset_pagination()
    st.session_state.pop("bank_local_audit_summary", None)
    st.session_state.pop("bank_local_audit_reports", None)
    st.session_state["bank_opec_context"] = bank_context_key

if active_opec is None:
    active_bank_items = []
    st.warning("Activa una OPEC en Mis OPEC para consultar o administrar su banco.")
else:
    active_bank_items = retain_training_partition(
        db,
        QuestionService.get_questions_for_user(
            db,
            u_id,
            include_review=True,
            competition_id=competition_id,
            user_opec=active_opec,
        ),
        active_opec,
    )
    st.caption(f"🎯 Banco aislado para la OPEC {active_opec_number}")
active_bank_ids = {str(item.question_id) for item in active_bank_items}
state_scope_key = bank_context_key.replace(":", "_")

if action == "Particiones del banco":
    st.subheader("Particiones del banco")
    st.caption(
        "Separa práctica, medición, anclaje y reserva mediante movimientos "
        "editoriales explícitos y trazables."
    )
    if not is_admin_user:
        st.error("Esta vista está restringida a administradores.")
    elif active_opec is None:
        st.warning("Activa una OPEC antes de administrar sus particiones.")
    elif not partition_schema_available(db):
        st.warning(
            "La base todavía no tiene completo el esquema canónico de particiones."
        )
    else:
        try:
            partition_context = resolve_active_bank_context(
                db,
                user_id=u_id,
                competition_id=competition_id,
            )
            counts = partition_counts(
                db,
                opec_profile_id=partition_context.opec_profile_id,
            )
        except BankPartitionError as exc:
            st.error(str(exc))
        else:
            partition_labels = {
                "training": "Entrenamiento",
                "measurement": "Medición",
                "anchor": "Anclaje",
                "reserved": "Reservado",
            }
            count_cols = st.columns(4)
            for column, partition in zip(count_cols, BANK_PARTITIONS):
                column.metric(partition_labels[partition], counts[partition])
            st.info(
                "Contenido y claves reservadas permanecen ocultos. Los aspirantes "
                "solo reciben material de entrenamiento apto para estudio."
            )

            source_partition = st.selectbox(
                "Partición de origen",
                BANK_PARTITIONS,
                format_func=lambda value: partition_labels[value],
                key=f"partition_source_{state_scope_key}",
            )
            target_options = [
                partition
                for partition in BANK_PARTITIONS
                if partition != source_partition
            ]
            target_partition = st.selectbox(
                "Partición de destino",
                target_options,
                format_func=lambda value: partition_labels[value],
                key=f"partition_target_{state_scope_key}_{source_partition}",
            )
            inventory = list_partition_items(
                db,
                opec_profile_id=partition_context.opec_profile_id,
                partition=source_partition,
                limit=25,
            )
            eligible_items = [item for item in inventory if item.eligible]
            blocked_count = len(inventory) - len(eligible_items)
            if source_partition == "reserved":
                st.caption(
                    "Los elementos reservados se identifican de forma opaca; esta "
                    "vista no consulta ni muestra enunciados, opciones o claves."
                )
            if blocked_count:
                st.warning(
                    f"{blocked_count} elemento(s) no cumplen todavía la barrera de "
                    "aptitud, revisión aprobada y cita precisa."
                )

            item_labels = {
                item.question_id: item.display_label for item in eligible_items
            }
            partition_nonce_key = (
                f"partition_nonce_{state_scope_key}_{source_partition}"
            )
            partition_nonce = int(st.session_state.get(partition_nonce_key, 0))
            selection_key = (
                f"partition_selection_{state_scope_key}_{source_partition}_"
                f"{partition_nonce}"
            )
            selected_partition_ids = st.multiselect(
                f"Selecciona hasta {MAX_PARTITION_BATCH} elementos",
                options=list(item_labels),
                format_func=lambda question_id: item_labels[question_id],
                key=selection_key,
            )
            batch_too_large = len(selected_partition_ids) > MAX_PARTITION_BATCH
            if batch_too_large:
                st.error(
                    f"Reduce el lote a máximo {MAX_PARTITION_BATCH} elementos."
                )
            movement_reason = st.text_area(
                "Motivo editorial del movimiento",
                placeholder="Explica por qué este lote cambia de función dentro del banco.",
                key=(
                    f"partition_reason_{state_scope_key}_{source_partition}_"
                    f"{partition_nonce}"
                ),
            )
            confirmed_move = st.checkbox(
                "Confirmo el movimiento editorial y su registro en una nueva revisión.",
                key=(
                    f"partition_confirm_{state_scope_key}_{source_partition}_"
                    f"{partition_nonce}"
                ),
            )
            can_move = (
                bool(selected_partition_ids)
                and not batch_too_large
                and len(movement_reason.strip()) >= 8
                and confirmed_move
            )
            if st.button(
                "Aplicar movimiento",
                type="primary",
                disabled=not can_move,
                use_container_width=True,
            ):
                try:
                    moves = move_question_partitions(
                        db,
                        context=partition_context,
                        question_ids=selected_partition_ids,
                        from_partition=source_partition,
                        to_partition=target_partition,
                        actor=st.session_state.get("username", "admin"),
                        reason=movement_reason,
                    )
                    db.commit()
                except BankPartitionError as exc:
                    db.rollback()
                    st.error(str(exc))
                except Exception:
                    db.rollback()
                    st.error(
                        "No se pudo aplicar el movimiento. Ningún elemento del lote "
                        "fue modificado."
                    )
                else:
                    st.session_state[partition_nonce_key] = partition_nonce + 1
                    st.success(
                        f"Movimiento registrado para {len(moves)} elemento(s)."
                    )
                    st.rerun()

elif action == "Centro de calidad":
    quality_questions = list(active_bank_items)
    quality_rows = []
    for question in quality_questions:
        state, detail, source = quality_state(question)
        quality_rows.append({
            "question": question,
            "state": state,
            "detail": detail,
            "source": source,
        })

    st.subheader("Centro de Calidad")
    st.caption("Control automático del banco. No presenta preguntas para aprobar una por una ni usa la IA como certificación.")
    state_counts = Counter(row["state"] for row in quality_rows)
    quality_cols = st.columns(4)
    quality_cols[0].metric("Listas para estudiar", state_counts["LISTA PARA ESTUDIAR"])
    quality_cols[1].metric("En contraste normativo", state_counts["EN CONTRASTE NORMATIVO"])
    quality_cols[2].metric("Corregir estructura", state_counts["CORREGIR ESTRUCTURA"])
    quality_cols[3].metric(
        "No usar / sin evidencia",
        state_counts["NO USAR"] + state_counts["SIN EVIDENCIA OFICIAL"],
    )
    st.info(
        "Las preguntas en contraste no entran a la práctica activa. Una fuente enlazada demuestra trazabilidad, "
        "pero no certifica todavía que la clave y la justificación interpreten correctamente la norma."
    )

    if st.button(
        "Actualizar diagnóstico automático",
        use_container_width=True,
        help="Revisa estructura y trazabilidad de todo el banco sin consumir IA ni cambiar qué preguntas están habilitadas.",
    ):
        try:
            for row in quality_rows:
                question = row["question"]
                store_deterministic_audit(question, audit_question_structure(question))
            db.commit()
            st.success(f"Diagnóstico actualizado para {len(quality_rows)} preguntas.")
            st.rerun()
        except Exception:
            db.rollback()
            st.error("No se pudo guardar el diagnóstico automático. Inténtalo nuevamente.")

    exceptions = [row for row in quality_rows if row["state"] != "LISTA PARA ESTUDIAR"]
    if exceptions:
        with st.expander(f"Ver {len(exceptions)} excepciones del banco"):
            table = []
            for row in exceptions:
                question = row["question"]
                source = row["source"] or assess_source_evidence(question)
                table.append({
                    "Estado": row["state"],
                    "Tema": question.topic or "Sin tema",
                    "Fuente declarada": question.source_refs or "Sin fuente",
                    "Artículo": source.get("article") or "—",
                    "Acción": row["detail"],
                })
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

    with st.expander("Cómo funciona este control"):
        st.markdown(
            "1. Comprueba la existencia de una fuente oficial enlazable.  \\n"
            "2. Valida estructura: situación, opciones, clave, justificación, tema y competencia.  \\n"
            "3. Excluye automáticamente material sin trazabilidad.  \\n"
            "4. Deja el contraste jurídico de fondo como una etapa separada y controlada."
        )

elif False:  # Legacy guided review kept temporarily for backwards-compatible deployments.
    queue_questions = list(active_bank_items)
    queue = queue_summary(queue_questions)
    ai_queue_state_key = f"ai_review_queue_{state_scope_key}"
    ai_queue_state = st.session_state.get(ai_queue_state_key)

    if ai_queue_state and ai_queue_state.get("remaining"):
        provider = ai_queue_state.get("provider", "Gemini")
        api_key = get_api_key(provider)
        if not api_key:
            st.session_state.pop(ai_queue_state_key, None)
            st.error("La auditoría por lote necesita una clave de IA configurada.")
        else:
            # Work in small visible batches. The old one-question rerun made
            # the page flash without giving the user usable progress feedback.
            batch_size = min(5, len(ai_queue_state["remaining"]))
            batch_progress = st.progress(
                ai_queue_state["completed"] / max(ai_queue_state["total"], 1),
                text=(f"Auditando {ai_queue_state['completed']} de "
                      f"{ai_queue_state['total']} candidatas…"),
            )
            auditor = LLMGenerator(provider, api_key)
            for _ in range(batch_size):
                question_id = ai_queue_state["remaining"][0]
                try:
                    ai_candidate = db.query(Question).filter(Question.question_id == question_id).first()
                    if (
                        ai_candidate is not None
                        and str(ai_candidate.question_id) in active_bank_ids
                        and queue_item(ai_candidate)
                        and not bool(ai_candidate.is_verified)
                        and needs_ai_audit(ai_candidate)
                    ):
                        ai_report = auditor.audit_question(
                            {
                                "topic": ai_candidate.topic,
                                "stem": ai_candidate.stem,
                                "options_json": ai_candidate.options_json,
                                "correct_key": ai_candidate.correct_key,
                                "rationale": ai_candidate.rationale,
                            },
                            source_context=str(ai_candidate.source_refs or ""),
                        )
                        if not isinstance(ai_report, dict):
                            raise ValueError("La IA no devolvió un informe estructurado.")
                        record_ai_audit(ai_candidate, ai_report)
                        db.commit()
                        if str(ai_report.get("status", "")).upper() == "ERROR":
                            ai_queue_state["errors"] = ai_queue_state.get("errors", 0) + 1
                            ai_queue_state["last_error"] = str(ai_report.get("critique", ""))
                        else:
                            ai_queue_state["successful"] = ai_queue_state.get("successful", 0) + 1
                        # Gemini free-tier quotas are burst-sensitive. A short
                        # pause avoids turning an entire batch into 429 errors.
                        if provider.lower() == "gemini":
                            time.sleep(GEMINI_AUDIT_REQUEST_DELAY_SECONDS)
                except Exception as audit_error:
                    print(
                        f"[AUDIT_QUEUE] {type(audit_error).__name__}",
                        file=sys.stderr,
                    )
                    db.rollback()
                    ai_queue_state["errors"] = ai_queue_state.get("errors", 0) + 1
                    ai_queue_state["last_error"] = (
                        "La candidata continúa pendiente por un error técnico "
                        f"({type(audit_error).__name__})."
                    )
                finally:
                    ai_queue_state["remaining"] = ai_queue_state["remaining"][1:]
                    ai_queue_state["completed"] += 1
                    batch_progress.progress(
                        ai_queue_state["completed"] / max(ai_queue_state["total"], 1),
                        text=(f"Auditando {ai_queue_state['completed']} de "
                              f"{ai_queue_state['total']} candidatas…"),
                    )

            if ai_queue_state["remaining"]:
                st.session_state[ai_queue_state_key] = ai_queue_state
                st.rerun()
            else:
                st.session_state.pop(ai_queue_state_key, None)
                st.session_state[f"ai_review_result_{state_scope_key}"] = {
                    "version": AI_AUDIT_RESULT_VERSION,
                    "total": ai_queue_state["total"],
                    "successful": ai_queue_state.get("successful", 0),
                    "errors": ai_queue_state.get("errors", 0),
                    "last_error": ai_queue_state.get("last_error", ""),
                }
                st.rerun()

    st.subheader("Revisión guiada de candidatas")
    queue_cols = st.columns(4)
    queue_cols[0].metric("Total en cola", queue["total"])
    queue_cols[1].metric("Pendientes", queue["pending"])
    queue_cols[2].metric("Aprobadas", queue["approved"])
    queue_cols[3].metric("Descartadas", queue["rejected"])
    st.progress(
        (queue["approved"] + queue["rejected"]) / queue["total"] if queue["total"] else 1.0,
        text=f"{queue['approved'] + queue['rejected']} de {queue['total']} candidatas decididas",
    )
    evidence_candidates = [
        question for question in queue_questions
        if queue_item(question)
        and not bool(question.is_verified)
        and (not isinstance(getattr(question, "quality_report", None), dict)
             or getattr(question, "quality_report", {}).get("status") != "REJECTED")
    ]
    evidence = [assess_source_evidence(question) for question in evidence_candidates]
    source_cols = st.columns(3)
    source_cols[0].metric("Fuente oficial enlazada", sum(
        item["status"] == "DIRECT_OFFICIAL_SOURCE" for item in evidence
    ))
    source_cols[1].metric("Ancla normativa detectada", sum(
        item["status"] == "OFFICIAL_CATALOG_MATCH" for item in evidence
    ))
    source_cols[2].metric("Sin evidencia suficiente", sum(
        item["status"] == "UNTRACEABLE" for item in evidence
    ))
    st.caption(
        "La fuente se comprueba antes de la IA: una ancla normativa requiere contraste "
        "con el texto oficial vigente; no habilita una pregunta por sí sola."
    )
    ai_result_key = f"ai_review_result_{state_scope_key}"
    ai_last_result = st.session_state.get(ai_result_key)
    if ai_last_result and ai_last_result.get("version") != AI_AUDIT_RESULT_VERSION:
        st.session_state.pop(ai_result_key, None)
        ai_last_result = None
    if ai_last_result:
        if ai_last_result["errors"]:
            st.warning(
                f"Última auditoría: {ai_last_result['successful']} analizadas y "
                f"{ai_last_result['errors']} con error técnico. Las fallidas siguen pendientes."
            )
        else:
            st.success(f"Auditoría IA completada: {ai_last_result['successful']} candidatas analizadas.")
    auto_rejections = [
        (question, automatic_rejection_reason(question))
        for question in queue_questions
        if queue_item(question)
        and not bool(question.is_verified)
        and (not isinstance(getattr(question, "quality_report", None), dict)
             or getattr(question, "quality_report", {}).get("status") != "REJECTED")
        and (automatic_rejection_reason(question) is not None)
    ]
    if auto_rejections:
        st.info(
            f"Clasificación automática disponible: {len(auto_rejections)} candidatas "
            "pueden descartarse sin revisión individual por fuente no verificable "
            "o dictamen IA de rechazo."
        )
        auto_confirm = st.checkbox(
            "Descartar automáticamente estas candidatas. No se aprobará ninguna de forma automática.",
            key=f"auto_reject_confirm_{state_scope_key}",
        )
        if st.button(
            "Descartar candidatas no confiables automáticamente",
            type="primary",
            use_container_width=True,
            disabled=not auto_confirm,
            key=f"auto_reject_start_{state_scope_key}",
        ):
            reviewer = st.session_state.get("username", "admin")
            try:
                for question, reason in auto_rejections:
                    save_queue_decision(question, reviewer, False, f"Automático: {reason}")
                db.commit()
                st.success(f"Se descartaron automáticamente {len(auto_rejections)} candidatas no confiables.")
                st.rerun()
            except Exception:
                db.rollback()
                st.error("No se pudo completar el descarte automático. Inténtalo nuevamente.")
    if ai_queue_state and ai_queue_state.get("remaining"):
        st.info(
            f"Auditoría IA en curso: {ai_queue_state['completed']} de "
            f"{ai_queue_state['total']} candidatas analizadas."
        )
    elif queue["pending"]:
        ai_provider = st.selectbox(
            "Proveedor para auditoría IA", ["Gemini", "OpenAI", "Mistral"],
            key=f"ai_queue_provider_{state_scope_key}",
        )
        ai_confirm = st.checkbox(
            "Auditar todas las pendientes con IA. Esta acción consume la clave configurada y no habilita preguntas.",
            key=f"ai_queue_confirm_{state_scope_key}",
        )
        if st.button(
            "Auditar toda la cola con IA", type="secondary", use_container_width=True,
            disabled=not ai_confirm, key=f"ai_queue_start_{state_scope_key}",
        ):
            if not get_api_key(ai_provider):
                st.error("Configura una clave de IA antes de iniciar la auditoría.")
            else:
                pending_questions = [
                    question
                    for question in queue_questions
                    if queue_item(question)
                    and not bool(question.is_verified)
                    and (not isinstance(getattr(question, "quality_report", None), dict)
                         or getattr(question, "quality_report", {}).get("status") != "REJECTED")
                ]
                pending_ids = [
                    str(question.question_id)
                    for question in pending_questions
                    if needs_ai_audit(question)
                ]
                if not pending_ids:
                    st.info("Todas las candidatas pendientes ya tienen una auditoría IA.")
                else:
                    st.session_state[ai_queue_state_key] = {
                        "remaining": pending_ids,
                        "completed": len(pending_questions) - len(pending_ids),
                        "total": len(pending_questions),
                        "provider": ai_provider,
                    }
                    st.rerun()

    candidate = queue["next_question"]
    if candidate is None:
        st.success("No hay candidatas pendientes en esta OPEC.")
    else:
        report = audit_question_structure(candidate)
        st.caption(f"Pendientes por revisar: {queue['pending']}")
        st.markdown(f"### {candidate.topic or 'Pregunta sin tema'}")
        st.markdown(f"**Enunciado:** {candidate.stem}")
        for key, value in (candidate.options_json or {}).items():
            st.write(f"**{key})** {value}")
        st.markdown(f"**Clave propuesta:** {candidate.correct_key}")
        st.caption(f"Justificación: {candidate.rationale or 'Sin justificación'}")
        st.caption(f"Fuente declarada: {candidate.source_refs or 'Sin fuente'}")
        source_evidence = assess_source_evidence(candidate)
        if source_evidence["status"] in {"DIRECT_OFFICIAL_SOURCE", "OFFICIAL_CATALOG_MATCH"}:
            article_note = (
                f" · Artículo detectado: {source_evidence['article']}"
                if source_evidence["article"] else ""
            )
            st.info(f"Evidencia de fuente: {source_evidence['reason']}{article_note}")
            if source_evidence["official_url"]:
                st.link_button("Consultar fuente oficial", source_evidence["official_url"])
        else:
            st.warning(f"Evidencia de fuente insuficiente: {source_evidence['reason']}")
        stored_ai_audit = (candidate.quality_report or {}).get("ai_audit")
        if isinstance(stored_ai_audit, dict):
            st.info(
                f"Recomendación IA: {stored_ai_audit.get('status', 'Sin estado')} · "
                f"puntaje {stored_ai_audit.get('score', '—')}/10"
            )
            if stored_ai_audit.get("critique"):
                st.caption(f"Análisis IA: {stored_ai_audit['critique']}")
        if report["status"] == "REVIEW":
            st.warning("El diagnóstico local encontró pendientes estructurales.")
            for finding in report["findings"]:
                st.write(f"- {finding['message']}")
        else:
            st.success("Diagnóstico local sin fallas estructurales. Verifica también la fuente de fondo.")

        candidate_report = dict(candidate.quality_report or {})
        source_verification = dict(candidate_report.get("source_verification") or {})
        editorial_metadata = dict(candidate_report.get("editorial_metadata") or {})
        evidence_url = source_verification.get("url") or source_evidence.get("official_url") or ""
        try:
            stored_verified_date = datetime.date.fromisoformat(
                str(source_verification.get("verified_on") or "")
            )
        except ValueError:
            stored_verified_date = datetime.date.today()
        inferred_function = function_number_for_question(
            candidate,
            active_opec.opec_number,
        ) or 1
        max_function = max(1, len(active_opec.functions or ()), int(inferred_function))
        current_function = int(editorial_metadata.get("function_number") or inferred_function)
        cognitive_labels = {
            "recognition": "Reconocimiento",
            "application": "Aplicación",
            "analysis": "Análisis",
            "judgment": "Juicio",
            "transfer": "Transferencia",
        }
        cognitive_options = [
            value
            for value in ("recognition", "application", "analysis", "judgment", "transfer")
            if value in COGNITIVE_LEVELS
        ]
        with st.expander("Fuente y ficha editorial obligatorias", expanded=True):
            with st.form(f"editorial_verification_{candidate.question_id}"):
                source_status = st.selectbox(
                    "Estado de la fuente",
                    ["official_current", "official_verified"],
                    index=(
                        1
                        if source_verification.get("status") == "official_verified"
                        else 0
                    ),
                    format_func=lambda value: {
                        "official_current": "Oficial vigente",
                        "official_verified": "Oficial verificada",
                    }[value],
                )
                source_url = st.text_input("URL oficial exacta", value=evidence_url)
                source_locator = st.text_input(
                    "Artículo, numeral o página",
                    value=str(source_verification.get("locator") or ""),
                )
                supporting_excerpt = st.text_area(
                    "Fragmento breve que sustenta la clave",
                    value=str(source_verification.get("supporting_excerpt") or ""),
                )
                verified_on = st.date_input(
                    "Fecha de contraste",
                    value=stored_verified_date,
                )
                subtopic = st.text_input(
                    "Subtema",
                    value=str(editorial_metadata.get("subtopic") or candidate.topic or ""),
                )
                cognitive_level = st.selectbox(
                    "Nivel cognitivo",
                    cognitive_options,
                    index=(
                        cognitive_options.index(editorial_metadata["cognitive_level"])
                        if editorial_metadata.get("cognitive_level") in cognitive_options
                        else cognitive_options.index("application")
                    ),
                    format_func=lambda value: cognitive_labels[value],
                )
                function_number = st.number_input(
                    "Función de la OPEC",
                    min_value=1,
                    max_value=max_function,
                    value=min(max(current_function, 1), max_function),
                    step=1,
                )
                editorial_difficulty = st.select_slider(
                    "Dificultad editorial interna",
                    options=list(range(1, 11)),
                    value=editorial_question_difficulty(candidate),
                )
                distractor_explanations = dict(
                    editorial_metadata.get("distractor_explanations") or {}
                )
                is_likert = (
                    str(candidate.question_type or "").upper() == "LIKERT"
                    or str(candidate.track or "").upper() in {"COMPORTAMENTAL", "INTEGRIDAD"}
                )
                if not is_likert:
                    st.markdown("**Por qué cada distractor no es la mejor respuesta**")
                    for option_key in candidate.options_json or {}:
                        if option_key == candidate.correct_key:
                            continue
                        distractor_explanations[option_key] = st.text_area(
                            f"Distractor {option_key}",
                            value=str(distractor_explanations.get(option_key) or ""),
                        )
                save_editorial = st.form_submit_button(
                    "Guardar contraste normativo y ficha editorial",
                    type="primary",
                    use_container_width=True,
                )
            if save_editorial:
                try:
                    record_editorial_verification(
                        candidate,
                        source_status=source_status,
                        source_url=source_url,
                        source_locator=source_locator,
                        supporting_excerpt=supporting_excerpt,
                        verified_on=verified_on.isoformat(),
                        verified_by=st.session_state.get("username", "admin"),
                        subtopic=subtopic,
                        cognitive_level=cognitive_level,
                        function_number=int(function_number),
                        editorial_difficulty=editorial_difficulty,
                        distractor_explanations=distractor_explanations,
                    )
                    db.commit()
                    st.success("Contraste guardado. La candidata ya puede pasar la validación final.")
                    st.rerun()
                except ValueError as exc:
                    db.rollback()
                    st.error(str(exc))

        validation_error = queue_validation_error(candidate, active_bank_items)
        if validation_error:
            st.error(validation_error)
        else:
            confirmation = st.checkbox(
                "Confirmo fuente, vigencia, clave, nivel cognitivo y análisis de distractores.",
                key=f"queue_confirm_{candidate.question_id}",
            )
            rejection_reason = st.text_input(
                "Motivo de descarte (opcional)", key=f"queue_reason_{candidate.question_id}"
            )
            approve_col, reject_col = st.columns(2)
            if approve_col.button(
                "Aprobar y continuar", disabled=not confirmation,
                use_container_width=True, type="primary", key=f"queue_approve_{candidate.question_id}",
            ):
                save_queue_decision(candidate, st.session_state.get("username", "admin"), True)
                db.commit()
                st.rerun()
            if reject_col.button(
                "Descartar y continuar", use_container_width=True,
                key=f"queue_reject_{candidate.question_id}",
            ):
                save_queue_decision(
                    candidate, st.session_state.get("username", "admin"), False, rejection_reason
                )
                db.commit()
                st.rerun()

elif action == "Consultar banco":
    bank_items = list(active_bank_items)
    pending_reinforcements = sum(is_reinforcement_candidate(item) for item in bank_items)
    safe_items = sum(is_safe_for_active_study(item) for item in bank_items)
    official_items = sum(question_format_status(item) == OFFICIAL_LABEL for item in bank_items)
    review_items = sum(question_format_status(item) == REVIEW_LABEL for item in bank_items)
    if is_admin_user:
        bank_cols = st.columns(4)
        bank_cols[0].metric("Banco total", len(bank_items))
        bank_cols[1].metric(
            "Aptas para estudiar", safe_items,
            help="Preguntas con fuente oficial, localizador, fragmento, vigencia y revisión individual completas.",
        )
        bank_cols[2].metric("Casos situacionales", official_items)
        bank_cols[3].metric("Requieren revisión", review_items)
        key_counts = Counter(item.correct_key for item in bank_items if item.correct_key)
        dominant_key, dominant_count = key_counts.most_common(1)[0] if key_counts else (None, 0)
        dominant_pct = dominant_count * 100 / len(bank_items) if bank_items else 0
        if dominant_pct >= 60:
            st.warning(
                f"Sesgo psicométrico: la opción {dominant_key} es correcta en "
                f"{dominant_count} de {len(bank_items)} preguntas ({dominant_pct:.0f}%). "
                "No se corregirá cambiando letras mecánicamente; exige reescritura y revisión."
            )
    local_audit_cols = st.columns([1, 2])
    if local_audit_cols[0].button(
        "🔬 Diagnóstico local del banco",
        use_container_width=True,
        help="Revisa estructura, trazabilidad y clasificación sin consumir IA ni aprobar preguntas.",
    ):
        summary = audit_bank(bank_items)
        # Cualquier aspirante puede consultar el diagnóstico. Solo un
        # administrador puede persistir el reporte en cada pregunta.
        if is_admin_user:
            for item in bank_items:
                store_deterministic_audit(item, summary["reports"][str(item.question_id)])
            db.commit()
        st.session_state["bank_local_audit_summary"] = {
            **{key: value for key, value in summary.items() if key != "reports"},
            "competition_id": competition_id,
            "opec_number": active_opec_number,
            "context_key": bank_context_key,
            "persisted": is_admin_user,
        }
        st.session_state["bank_local_audit_reports"] = summary["reports"]
        st.rerun()
    local_summary = st.session_state.get("bank_local_audit_summary")
    if local_summary and local_summary.get("context_key") == bank_context_key:
        storage_note = "Reporte guardado." if local_summary.get("persisted") else "Consulta de solo lectura."
        local_audit_cols[1].info(
            f"Diagnóstico local: {local_summary['passed']} sin fallas estructurales · "
            f"{local_summary['review']} requieren revisión · clave dominante "
            f"{local_summary['dominant_key'] or '—'} ({local_summary['dominant_key_pct']:.0f}%). "
            f"Posibles duplicados: {local_summary.get('near_duplicate_count', 0)}. "
            f"{storage_note} Este control no certifica la exactitud jurídica."
        )
    if is_admin_user and pending_reinforcements:
        st.info(
            f"🧪 Hay **{pending_reinforcements} refuerzos generados** pendientes de revisión. "
            "Selecciónalos en el filtro Calidad."
        )

    # FILTERS
    col_filters = st.columns([2, 1, 1, 1, 1, 1])
    with col_filters[0]:
        search = st.text_input("🔍 Buscar en enunciado o justificación...")
    with col_filters[1]:
        track_f = st.selectbox(
            "Área del banco",
            ["Todos", "FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"],
            help="Clasificación interna de práctica; no equivale a ejes oficiales del examen.",
        )
    with col_filters[2]:
        diff_f = st.multiselect(
            "Dificultad editorial",
            list(range(1, 11)),
            format_func=lambda value: f"Nivel {value}",
        )
    with col_filters[3]:
        # Quality Filter Mikey v36
        quality_f = st.selectbox(
            "Calidad",
            [QUALITY_ALL, QUALITY_LOCAL_REVIEW, QUALITY_REINFORCEMENTS, QUALITY_VERIFIED, QUALITY_PENDING],
            on_change=reset_pagination,
        )
    with col_filters[4]:
        format_f = st.selectbox("Formato", ["Todos", OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL])
    with col_filters[5]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state["bulk_selection"]:
            st.markdown(f"### ⚙️ Acciones Masivas ({len(st.session_state['bulk_selection'])} ítems seleccionados)")
            col_audit, col_del_real = st.columns([1, 1])
            
            with col_audit:
                # v34.1 Bulk Audit Button Mikey
                if st.button(
                    f"🛡️ Auditar Selección", type="primary", use_container_width=True,
                    disabled=not is_admin_user,
                    help="Solo administradores. La IA orienta la revisión, pero no certifica la pregunta.",
                ):
                    try:
                        provider = st.session_state.get("current_provider", "Gemini")
                        api_key = get_api_key(provider)
                        if api_key:
                            gen = LLMGenerator(provider, api_key)
                            if not hasattr(gen, 'audit_question'):
                                st.warning("⏳ Esperando actualización del servidor. Reintenta en 30s.")
                            else:
                                prog_audit = st.progress(0, text="Iniciando Auditoría Masiva...")
                                selection = [
                                    question_id
                                    for question_id in st.session_state["bulk_selection"]
                                    if str(question_id) in active_bank_ids
                                ]
                                for i, qid in enumerate(selection):
                                    prog_audit.progress((i + 1) / len(selection), text=f"Auditando {i+1} de {len(selection)}...")
                                    q_aud = db.query(Question).get(qid)
                                    if (
                                        q_aud
                                        and str(q_aud.question_id) in active_bank_ids
                                        and not q_aud.is_verified
                                    ):
                                        report = gen.audit_question({
                                            "topic": q_aud.topic, "stem": q_aud.stem, 
                                            "options_json": q_aud.options_json, 
                                            "correct_key": q_aud.correct_key, 
                                            "rationale": q_aud.rationale
                                        })
                                        record_ai_audit(q_aud, report)
                                        # El dictamen de IA se conserva como ayuda; la aprobación
                                        # para estudiar requiere comprobación normativa separada.
                                    
                                    # Delay to avoid 429 Rate Limit Mikey v39
                                    time.sleep(1.5) 
                                db.commit()
                                st.success("¡Auditoría masiva completada!")
                                st.rerun()
                        else:
                            st.error("Falta API Key")
                    except Exception as e:
                        db.rollback()
                        log_ui_exception("question_bank.bulk_audit", e)
                        st.error("No fue posible completar la auditoría masiva.")

            with col_del_real:
                if st.button(
                    f"🗑️ Borrar Selección", type="secondary", use_container_width=True,
                    disabled=not is_admin_user,
                    help="Solo los administradores pueden eliminar preguntas.",
                ):
                    try:
                        for qid in st.session_state["bulk_selection"]:
                            q_to_del = db.query(Question).get(qid)
                            if q_to_del and str(q_to_del.question_id) in active_bank_ids:
                                db.delete(q_to_del)
                        db.commit()
                        reset_selection()
                        st.success("Preguntas eliminadas.")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        log_ui_exception("question_bank.bulk_delete", e)
                        st.error("No fue posible eliminar la selección.")
            
            st.divider()
            
            # Export Logic
            selected_qs = db.query(Question).filter(
                Question.question_id.in_(list(st.session_state["bulk_selection"]))
            ).all()
            selected_qs = retain_allowed_questions(selected_qs, active_bank_ids)
            
            if selected_qs:
                st.markdown("### 📥 Exportar Seleccionadas")
                col_down_ex, col_down_txt = st.columns([1, 1])
                
                # 1. Excel Export
                export_data = []
                for q in selected_qs:
                    opts = q.options_json if q.options_json else {}
                    export_data.append({
                        'track': q.track,
                        'competency': q.competency,
                        'topic': q.topic,
                        'difficulty': editorial_question_difficulty(q),
                        'stem': q.stem,
                        'options_A': opts.get('A', ''),
                        'options_B': opts.get('B', ''),
                        'options_C': opts.get('C', ''),
                        'options_D': opts.get('D', ''),
                        'correct_key': q.correct_key,
                        'rationale': q.rationale
                    })
                df_exp = pd.DataFrame(export_data)
                topo_ex = io.BytesIO()
                with pd.ExcelWriter(topo_ex, engine='openpyxl') as writer:
                    df_exp.to_excel(writer, index=False)
                
                with col_down_ex:
                    st.download_button(
                        "📥 Descargar Excel",
                        data=topo_ex.getvalue(),
                        file_name=f"Seleccion_Preguntas_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                # 2. Text Export
                lines = ["track|competency|topic|stem|options_A|options_B|options_C|options_D|correct_key|rationale|difficulty"]
                for d in export_data:
                    line = "|".join([
                        str(d['track']), str(d['competency']), str(d['topic']), 
                        str(d['stem']).replace("\n", " "), 
                        str(d['options_A']), str(d['options_B']), str(d['options_C']), str(d['options_D']),
                        str(d['correct_key']), str(d['rationale']).replace("\n", " "), str(d['difficulty'])
                    ])
                    lines.append(line)
                
                with col_down_txt:
                    st.download_button(
                        "📄 Descargar Texto (|)",
                        data="\n".join(lines),
                        file_name=f"Seleccion_Preguntas_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

    # Todos los filtros parten del mismo inventario OPEC. No existe una ruta
    # alternativa que vuelva a consultar el concurso completo.
    filtered = []
    local_reports = st.session_state.get("bank_local_audit_reports", {})
    for q in bank_items:
        searchable = f"{q.stem or ''} {q.rationale or ''}".lower()
        if search and search.lower() not in searchable:
            continue
        if track_f != "Todos" and q.track != track_f:
            continue
        if diff_f and editorial_question_difficulty(q) not in diff_f:
            continue
        if not is_admin_user and not is_safe_for_active_study(q):
            continue
        if quality_f == QUALITY_LOCAL_REVIEW:
            if local_reports.get(str(q.question_id), {}).get("status") != "REVIEW":
                continue
        elif not matches_quality_filter(q, quality_f):
            continue
        if format_f != "Todos" and question_format_status(q) != format_f:
            continue
        filtered.append(q)

    total_count = len(filtered)
    PAGE_SIZE = 20
    st.session_state["page_num"] = min(
        st.session_state["page_num"], max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    )
    offset = (st.session_state["page_num"] - 1) * PAGE_SIZE
    questions = filtered[offset:offset + PAGE_SIZE]
    if is_admin_user:
        visible_safe = sum(is_safe_for_active_study(item) for item in filtered)
        st.info(
            f"🎯 **OPEC {active_opec_number or '—'}:** "
            f"{total_count} registros coinciden con los filtros; "
            f"{visible_safe} están habilitados para estudio."
        )
    else:
        st.info(
            f"🎯 **OPEC {active_opec_number or '—'}:** "
            f"{total_count} preguntas aptas para tu preparación."
        )
    
    if not questions:
        st.warning("No hay preguntas que coincidan con la búsqueda.")
    else:
        if is_admin_user:
            col_m_sel, col_m_unsel = st.columns([1, 1])
            with col_m_sel:
                if st.button("✅ Seleccionar visibles", use_container_width=True):
                    for q in questions:
                        st.session_state["bulk_selection"].add(q.question_id)
                        st.session_state[f"sel_{q.question_id}"] = True
                    st.rerun()
            with col_m_unsel:
                if st.button("❌ Limpiar selección", use_container_width=True):
                    reset_selection()
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        for q in questions:
            diff_tags = {
                value: "🟢" if value <= 3 else "🟡" if value <= 7 else "🔴"
                for value in range(1, 11)
            }
            is_selected = q.question_id in st.session_state["bulk_selection"]
            
            if is_admin_user:
                col_sel, col_exp = st.columns([0.05, 0.95])
                with col_sel:
                    if st.checkbox("Seleccionar", value=is_selected, key=f"sel_{q.question_id}", label_visibility="collapsed"):
                        st.session_state["bulk_selection"].add(q.question_id)
                    else:
                        st.session_state["bulk_selection"].discard(q.question_id)
            else:
                col_exp = st.container()
            
            with col_exp:
                status_icon = "✅" if getattr(q, 'is_verified', False) else "⏳"
                format_status = question_format_status(q)
                format_icon = "PJS REVISADA" if format_status == OFFICIAL_LABEL else "PRÁCTICA" if format_status == PRACTICE_LABEL else "REVISAR"
                display_title = (
                    f"{status_icon} {format_icon} "
                    f"{diff_tags.get(editorial_question_difficulty(q), '⚪')} "
                    f"[{q.track or 'SIN ÁREA'}] {q.stem[:80]}..."
                )
                with st.expander(display_title):
                    transient_local_report = st.session_state.get(
                        "bank_local_audit_reports", {}
                    ).get(str(q.question_id))
                    if transient_local_report and transient_local_report.get("status") == "REVIEW":
                        st.warning(
                            f"Diagnóstico local: {transient_local_report.get('score', 0)}/100. "
                            "Esta pregunta requiere revisión."
                        )
                        for finding in transient_local_report.get("findings", []):
                            st.write(f"- {finding.get('message')}")
                    st.caption(f"Formato: {format_status}")
                    st.markdown(f"**Enunciado:**\n{q.stem}")
                    ops = q.options_json if q.options_json else {}
                    if ops:
                        cols_ops = st.columns(2)
                        for i, (key, val) in enumerate(ops.items()):
                            cols_ops[i % 2].markdown(f"**{key})** {val}")
                    
                    if q.correct_key:
                        st.markdown(f"**Respuesta correcta:** :green[{q.correct_key}]")
                    else:
                        st.markdown("**Escala de autorreporte:** sin respuesta correcta")
                    if q.rationale:
                        st.caption(f"Justificación: {q.rationale}")
                    if q.source_refs:
                        st.caption(f"Fuente: {q.source_refs}")

                    if is_pending_review_candidate(q):
                        if is_reinforcement_candidate(q):
                            st.warning("Refuerzo generado por IA: pendiente de comprobación normativa.")
                        else:
                            st.warning("Pregunta candidata: requiere comprobación individual antes de entrar al estudio activo.")
                        validation_error = candidate_validation_error(q)
                        if validation_error:
                            st.error(validation_error)
                        elif is_admin_user:
                            confirmation = st.checkbox(
                                "Revisé el enunciado, la clave, la justificación y la fuente.",
                                key=f"confirm_candidate_{q.question_id}",
                            )
                            approve_col, reject_col = st.columns(2)
                            if approve_col.button(
                                "✅ Aprobar para práctica",
                                key=f"approve_candidate_{q.question_id}",
                                disabled=not confirmation,
                                use_container_width=True,
                            ):
                                approve_candidate(q, st.session_state.get("username", "admin"))
                                db.commit()
                                st.success("Pregunta aprobada. Ya puede entrar en la práctica activa.")
                                st.rerun()
                            if reject_col.button(
                                "⛔ Descartar candidato",
                                key=f"reject_candidate_{q.question_id}",
                                use_container_width=True,
                            ):
                                reject_candidate(q, st.session_state.get("username", "admin"))
                                db.commit()
                                st.success("Candidato descartado y conservado para trazabilidad.")
                                st.rerun()
                        else:
                            st.info("Solo un administrador puede aprobar o descartar este candidato.")
                    
                    st.divider()
                    col_act1, col_act2, col_act3 = st.columns([1, 1, 1])
                    
                    with col_act1:
                        if st.button(
                            "🛡️ Auditar con IA", key=f"audit_{q.question_id}",
                            use_container_width=True, disabled=not is_admin_user,
                            help="Solo administradores. El resultado no activa automáticamente la pregunta.",
                        ):
                            with st.spinner("Realizando auditoría técnica..."):
                                try:
                                    provider = st.session_state.get("current_provider", "Gemini")
                                    api_key = get_api_key(provider)
                                    if api_key:
                                        gen = LLMGenerator(provider, api_key)
                                        
                                        # Resilient Attribute Check Mikey v33
                                        if hasattr(gen, 'audit_question'):
                                            report = gen.audit_question({
                                                "topic": q.topic, "stem": q.stem, 
                                                "options_json": q.options_json, 
                                                "correct_key": q.correct_key, 
                                                "rationale": q.rationale
                                            })
                                            record_ai_audit(q, report)
                                            # La IA orienta la revisión, pero no habilita por sí
                                            # sola una pregunta para el estudio activo.
                                            db.commit()
                                            st.success(f"Auditoría completada: {report.get('score')}/10")
                                            st.rerun()
                                        else:
                                            st.warning("⏳ El motor de IA no respondió. Espera 30 segundos y vuelve a intentar.")
                                    else:
                                        st.error("Falta API Key")
                                except Exception as e:
                                    log_ui_exception("question_bank.single_audit", e)
                                    st.error("No fue posible completar la auditoría técnica.")

                    with col_act2:
                        if st.button(
                            "🗑️ Eliminar", key=f"del_single_{q.question_id}", type="secondary",
                            use_container_width=True, disabled=not is_admin_user,
                            help="Solo los administradores pueden eliminar preguntas.",
                        ):
                            db.delete(q)
                            db.commit()
                            st.rerun()
                            
                    with col_act3:
                        # Psychometric Insight Mikey
                        hits = getattr(q, 'global_hits', 0)
                        misses = getattr(q, 'global_misses', 0)
                        total = hits + misses
                        disc_idx = (hits / total * 100) if total > 0 else 0
                        st.caption(f"⚡ Índice de Acierto Global: {disc_idx:.0f}%")
                    
                    if getattr(q, 'quality_report', None):
                        with st.expander("📄 Ver Reporte de Auditoría", expanded=False):
                            rep = q.quality_report
                            local_rep = rep.get("deterministic_audit") if isinstance(rep, dict) else None
                            if local_rep:
                                st.markdown(
                                    f"**Diagnóstico local:** {local_rep.get('score', 0)}/100 · "
                                    f"{local_rep.get('status', 'REVIEW')}"
                                )
                                for finding in local_rep.get("findings", []):
                                    st.write(f"- {finding.get('message')}")
                            ai_rep = rep.get("ai_audit") if isinstance(rep.get("ai_audit"), dict) else rep
                            score = ai_rep.get("score", "Sin calificar")
                            st.markdown(f"**Score IA:** {score}/10 | **Estado de control:** {rep.get('status')}")
                            st.write(f"**Crítica:** {ai_rep.get('critique', 'Sin observaciones')}")
                            st.write("**Hallazgos:**")
                            for f in ai_rep.get('findings', []):
                                st.write(f"- {f}")
                            st.info(f"💡 **Sugerencia:** {ai_rep.get('suggestion', 'Sin sugerencias')}")

        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
        st.caption(f"Página {min(st.session_state['page_num'], total_pages)} de {total_pages}")
        page_cols = st.columns(2)
        if page_cols[0].button("⬅️ Anterior", disabled=st.session_state["page_num"] <= 1, use_container_width=True):
            st.session_state["page_num"] -= 1
            st.rerun()
        if page_cols[1].button("➡️ Siguiente", disabled=st.session_state["page_num"] >= total_pages, use_container_width=True):
            st.session_state["page_num"] += 1
            st.rerun()

elif action == "Importar archivo":
    if active_opec is None:
        st.error("Activa una OPEC antes de importar preguntas.")
        st.stop()
    st.info("Sube un archivo `.xlsx` o `.csv`. Columnas requeridas: `track, competency, topic, stem, options_A, options_B, options_C, options_D, correct_key, rationale` (opcional)")
    
    # --- TEMPLATE DOWNLOAD ---
    template_data = {
        'track': ['FUNCIONAL', 'COMPORTAMENTAL', 'INTEGRIDAD'],
        'competency': ['Gestión Tributaria', 'Orientación al Logro', 'Ética'],
        'topic': ['IVA', 'Trabajo en Equipo', 'Valores'],
        'stem': ['SITUACIÓN: Un contribuyente... PREGUNTA: ¿Qué hacer?', 'SITUACIÓN: Caso de equipo...', 'SITUACIÓN: Dilema ético...'],
        'options_A': ['Opción 1', 'Valor 1', 'Acción 1'],
        'options_B': ['Opción 2', 'Valor 2', 'Acción 2'],
        'options_C': ['Opción 3', 'Valor 3', 'Acción 3'],
        'options_D': ['Opción 4', 'Valor 4', 'Acción 4'],
        'correct_key': ['A', 'B', 'C'],
        'rationale': ['Explicación A', 'Explicación B', 'Explicación C'],
        'difficulty': [2, 1, 3]
    }
    df_template = pd.DataFrame(template_data)
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Descargar Plantilla Excel (.xlsx)",
        data=towrite.getvalue(),
        file_name="Plantilla_Preguntas_DIAN.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.divider()
    
    uploaded = st.file_uploader("Archivo de preguntas", type=["csv", "xlsx"])
    
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            
            st.success(f"Archivo leído: {len(df)} filas detectadas.")
            
            # VALIDATION
            is_valid, err_list = validate_import_df(df)
            
            if not is_valid:
                st.error("📉 El archivo tiene errores de estructura o datos:")
                for err in err_list[:15]: # Limit display
                    st.write(f"- {err}")
                if len(err_list) > 15:
                    st.write(f"... y {len(err_list)-15} errores más.")
                st.stop()
            else:
                st.success("✅ Estructura validada correctamente.")
                with st.expander("Previsualizar datos"):
                    st.dataframe(df.head())
                
                if st.button("🚀 Procesar e Importar", type="primary"):
                    count_ok = 0
                    count_dupe = 0
                    
                    existing_hashes = [q.hash_norm for q in db.query(Question.hash_norm).all()]
                    existing_stems = [value for (value,) in db.query(Question.stem).all()]
                    
                    progress = st.progress(0)
                    for index, row in df.iterrows():
                        progress.progress((index + 1) / len(df))
                        stem = str(row['stem'])
                        h = compute_hash(stem)
                        
                        if h in existing_hashes:
                            count_dupe += 1
                            continue
                        if find_duplicates(stem, existing_stems, threshold=92):
                            count_dupe += 1
                            continue
                        track_value = str(row['track']).upper()
                        is_likert = track_value in {"COMPORTAMENTAL", "INTEGRIDAD"}
                            
                        ops = {
                            "A": str(row['options_A']),
                            "B": str(row['options_B']),
                            "C": str(row['options_C']),
                        }
                        if is_likert:
                            ops["D"] = str(row['options_D'])
                        
                        # Safe difficulty conversion
                        raw_diff = row.get('difficulty', 2)
                        try:
                            editorial_difficulty = int(float(raw_diff)) if not pd.isna(raw_diff) else 5
                        except (ValueError, TypeError):
                            editorial_difficulty = 5
                        editorial_difficulty = min(max(editorial_difficulty, 1), 10)
                        legacy_difficulty = (
                            1 if editorial_difficulty <= 3
                            else 2 if editorial_difficulty <= 7
                            else 3
                        )
                            
                        q = Question(
                            competition_id=competition_id,
                            question_id=str(uuid.uuid4()),
                            track=track_value,
                            competency=str(row.get('competency', 'General')),
                            topic=str(row.get('topic', 'General')),
                            difficulty=legacy_difficulty,
                            question_type="LIKERT" if is_likert else "SITUATIONAL",
                            stem=stem,
                            options_json=ops,
                            correct_key=(
                                None
                                if is_likert
                                else str(row['correct_key']).strip().upper()
                            ),
                            rationale=str(row.get('rationale', '')),
                            source_refs=str(row.get('source_refs', '') or ''),
                            hash_norm=h,
                            is_verified=False,
                            quality_report={
                                "origin": "manual_question_review",
                                "status": "PENDING_HUMAN_REVIEW",
                                "editorial_difficulty_1_10": editorial_difficulty,
                            },
                        )
                        db.add(q)
                        assign_question_to_opec(db, q, active_opec)
                        count_ok += 1
                        existing_hashes.append(h) # Update local cache for batch
                        existing_stems.append(stem)
                    
                    db.commit()
                    st.balloons()
                    st.success(f"¡Importación Finalizada! Nuevas: {count_ok} | Duplicadas omitidas: {count_dupe}")

        except Exception as e:
            log_ui_exception("question_bank.import", e)
            st.error("No fue posible procesar el archivo. Revisa su formato e inténtalo de nuevo.")

elif action == "Crear manualmente":
    if active_opec is None:
        st.error("Activa una OPEC antes de crear preguntas.")
        st.stop()
    with st.form("manual_create"):
        st.subheader("Nueva Pregunta")
        col1, col2 = st.columns(2)
        with col1:
            track = st.selectbox(
                "Área del banco",
                ["FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"],
                help="Clasificación interna para organizar el banco.",
            )
            topic = st.text_input("Tema")
            competency = st.text_input("Competencia")
        with col2:
            stem = st.text_area("Enunciado de la Pregunta")
            difficulty = st.select_slider(
                "Dificultad editorial interna",
                options=list(range(1, 11)),
                value=5,
            )
            source_refs = st.text_input(
                "Fuente declarada",
                help="La pregunta seguirá como candidata hasta contrastar URL, localizador y vigencia.",
            )
            
        st.markdown("---")
        st.markdown("**Opciones de Respuesta**")
        c1, c2 = st.columns(2)
        with c1:
            op_a = st.text_input("Opción A")
            op_b = st.text_input("Opción B")
        with c2:
            op_c = st.text_input("Opción C")
            op_d = (
                st.text_input("Opción D")
                if track in {"COMPORTAMENTAL", "INTEGRIDAD"}
                else ""
            )
            
        col_correct, col_rationale = st.columns([1, 2])
        with col_correct:
            correct = (
                None
                if track in {"COMPORTAMENTAL", "INTEGRIDAD"}
                else st.selectbox("Respuesta correcta propuesta", ["A", "B", "C"])
            )
            if correct is None:
                st.caption("El autorreporte Likert no tiene clave correcta.")
        with col_rationale:
            rationale = st.text_area("Justificación / Explicación")
        
        if st.form_submit_button("Guardar Pregunta", type="primary"):
            h = compute_hash(stem)
            if db.query(Question).filter_by(hash_norm=h).first():
                st.error("¡Pregunta idéntica ya existe!")
            elif find_duplicates(
                stem,
                [value for (value,) in db.query(Question.stem).all()],
                threshold=92,
            ):
                st.error("Existe una pregunta demasiado similar. Reescríbela antes de guardarla.")
            else:
                is_likert = track in {"COMPORTAMENTAL", "INTEGRIDAD"}
                options = {"A": op_a, "B": op_b, "C": op_c}
                if is_likert:
                    options["D"] = op_d
                q = Question(
                    competition_id=competition_id,
                    question_id=str(uuid.uuid4()),
                    track=track,
                    competency=competency or "Pendiente de clasificación",
                    topic=topic,
                    stem=stem,
                    difficulty=difficulty,
                    question_type="LIKERT" if is_likert else "SITUATIONAL",
                    options_json=options,
                    correct_key=correct,
                    rationale=rationale,
                    source_refs=source_refs,
                    hash_norm=h,
                    is_verified=False,
                    quality_report={
                        "origin": "manual_question_review",
                        "status": "PENDING_HUMAN_REVIEW",
                        "editorial_difficulty_1_10": difficulty,
                    },
                )
                db.add(q)
                assign_question_to_opec(db, q, active_opec)
                db.commit()
                st.success("Candidata guardada. Aún requiere contraste normativo y revisión editorial.")

db.close()
