import streamlit as st
import pandas as pd
import os, sys, uuid, datetime, io, time
from collections import Counter

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import Question
from core.dedupe import compute_hash, find_duplicates
from core.import_utils import validate_import_df
from core.generators.llm import LLMGenerator
from core.config import get_api_key
from ui_utils import load_css, render_header, render_custom_sidebar

from core.auth import AuthManager
from core.competitions import get_active_competition_id
from core.exam_format import (
    OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL, question_format_status,
)
from core.legacy_question_audit import is_safe_for_active_study
from core.question_review import (
    QUALITY_ALL, QUALITY_PENDING, QUALITY_REINFORCEMENTS, QUALITY_VERIFIED,
    approve_candidate, candidate_validation_error, is_reinforcement_candidate,
    matches_quality_filter, record_ai_audit, reject_candidate,
)

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

QUALITY_LOCAL_REVIEW = "Diagnóstico local: revisar 🔬"

AI_AUDIT_RESULT_VERSION = "v2"


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


def queue_validation_error(question):
    options = getattr(question, "options_json", None)
    if not str(getattr(question, "source_refs", "") or "").strip():
        return "Falta una fuente verificable."
    if not str(getattr(question, "stem", "") or "").strip():
        return "Falta el enunciado."
    if not isinstance(options, dict) or set(options) != {"A", "B", "C"}:
        return "La candidata debe tener exactamente tres opciones: A, B y C."
    if getattr(question, "correct_key", None) not in options:
        return "La clave no corresponde a una opción disponible."
    if not str(getattr(question, "rationale", "") or "").strip():
        return "Falta la justificación de la respuesta."
    return None


def save_queue_decision(question, reviewer, approved, reason=""):
    report = dict(getattr(question, "quality_report", None) or {})
    report.update(
        status="APPROVED" if approved else "REJECTED",
        review="human_source_grounded" if approved else "human_rejected",
        origin=report.get("origin", "manual_question_review"),
        reviewed_by=reviewer,
        reviewed_at=datetime.date.today().isoformat(),
        rejection_reason="" if approved else reason.strip(),
    )
    question.quality_report = report
    question.is_verified = bool(approved)

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

stats_s, rank = render_custom_sidebar()

is_admin_user = AuthManager.is_admin()
available_actions = ["Consultar banco"]
if is_admin_user:
    available_actions.extend(["Revisión guiada", "Importar archivo", "Crear manualmente"])
action = st.selectbox("Vista", available_actions, label_visibility="collapsed")
st.divider()

db = SessionLocal()

if not is_admin_user:
    st.info("Modo consulta: solo los administradores pueden crear, auditar o eliminar preguntas.")

# OPEC Focus Toggle Mikey v6.4
u_id = st.session_state.get("user_id")
from services.question_service import QuestionService

# Detect if user has active OPEC to set default
from db.models import UserOPEC
has_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first() is not None

opec_focus = st.toggle("🎯 Enfoque por mi OPEC (Alta Precisión)", 
                       value=has_opec, 
                       help="Muestra solo preguntas que coinciden con las funciones y naturaleza de tu cargo configurado.")

if action == "Revisión guiada":
    competition_id = get_active_competition_id(db, u_id)
    queue_query = db.query(Question)
    if competition_id is not None:
        queue_query = queue_query.filter(Question.competition_id == competition_id)
    queue = queue_summary(queue_query.all())
    ai_queue_state_key = f"ai_review_queue_{competition_id}"
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
                except Exception as audit_error:
                    print(f"[AUDIT_QUEUE] {audit_error}", file=sys.stderr)
                    db.rollback()
                    ai_queue_state["errors"] = ai_queue_state.get("errors", 0) + 1
                    ai_queue_state["last_error"] = str(audit_error)
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
                st.session_state[f"ai_review_result_{competition_id}"] = {
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
    ai_last_result = st.session_state.get(f"ai_review_result_{competition_id}")
    if ai_last_result and ai_last_result.get("version") != AI_AUDIT_RESULT_VERSION:
        st.session_state.pop(f"ai_review_result_{competition_id}", None)
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
        for question in queue_query.all()
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
            key=f"auto_reject_confirm_{competition_id}",
        )
        if st.button(
            "Descartar candidatas no confiables automáticamente",
            type="primary",
            use_container_width=True,
            disabled=not auto_confirm,
            key=f"auto_reject_start_{competition_id}",
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
            key=f"ai_queue_provider_{competition_id}",
        )
        ai_confirm = st.checkbox(
            "Auditar todas las pendientes con IA. Esta acción consume la clave configurada y no habilita preguntas.",
            key=f"ai_queue_confirm_{competition_id}",
        )
        if st.button(
            "Auditar toda la cola con IA", type="secondary", use_container_width=True,
            disabled=not ai_confirm, key=f"ai_queue_start_{competition_id}",
        ):
            if not get_api_key(ai_provider):
                st.error("Configura una clave de IA antes de iniciar la auditoría.")
            else:
                pending_questions = [
                    question
                    for question in queue_query.all()
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

        validation_error = queue_validation_error(candidate)
        if validation_error:
            st.error(validation_error)
        else:
            confirmation = st.checkbox(
                "Confirmo que verifiqué fuente, vigencia, enunciado, clave y justificación.",
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
    competition_id = get_active_competition_id(db, u_id)
    pending_query = db.query(Question)
    if competition_id is not None:
        pending_query = pending_query.filter(Question.competition_id == competition_id)
    bank_items = pending_query.all()
    pending_reinforcements = sum(is_reinforcement_candidate(item) for item in bank_items)
    safe_items = sum(is_safe_for_active_study(item) for item in bank_items)
    official_items = sum(question_format_status(item) == OFFICIAL_LABEL for item in bank_items)
    review_items = sum(question_format_status(item) == REVIEW_LABEL for item in bank_items)
    if is_admin_user:
        bank_cols = st.columns(4)
        bank_cols[0].metric("Banco total", len(bank_items))
        bank_cols[1].metric(
            "Aptas para estudiar", safe_items,
            help="Preguntas con fuente revisada o una decisión conservadora de auditoría.",
        )
        bank_cols[2].metric("Casos GOA", official_items)
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
            "persisted": is_admin_user,
        }
        st.session_state["bank_local_audit_reports"] = summary["reports"]
        st.rerun()
    local_summary = st.session_state.get("bank_local_audit_summary")
    if local_summary and local_summary.get("competition_id") == competition_id:
        storage_note = "Reporte guardado." if local_summary.get("persisted") else "Consulta de solo lectura."
        local_audit_cols[1].info(
            f"Diagnóstico local: {local_summary['passed']} sin fallas estructurales · "
            f"{local_summary['review']} requieren revisión · clave dominante "
            f"{local_summary['dominant_key'] or '—'} ({local_summary['dominant_key_pct']:.0f}%). "
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
        track_f = st.selectbox("Eje", ["Todos", "FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"])
    with col_filters[2]:
        diff_f = st.multiselect("Dificultad", [1, 2, 3], format_func=lambda x: {1: "🟢 Básico", 2: "🟡 Intermedio", 3: "🔴 Avanzado"}[x])
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
                                selection = list(st.session_state["bulk_selection"])
                                for i, qid in enumerate(selection):
                                    prog_audit.progress((i + 1) / len(selection), text=f"Auditando {i+1} de {len(selection)}...")
                                    q_aud = db.query(Question).get(qid)
                                    if q_aud and not q_aud.is_verified:
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
                        st.error(f"Error en auditoría masiva: {e}")

            with col_del_real:
                if st.button(
                    f"🗑️ Borrar Selección", type="secondary", use_container_width=True,
                    disabled=not is_admin_user,
                    help="Solo los administradores pueden eliminar preguntas.",
                ):
                    try:
                        for qid in st.session_state["bulk_selection"]:
                            q_to_del = db.query(Question).get(qid)
                            if q_to_del: db.delete(q_to_del)
                        db.commit()
                        reset_selection()
                        st.success("Preguntas eliminadas.")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error: {e}")
            
            st.divider()
            
            # Export Logic
            selected_qs = db.query(Question).filter(Question.question_id.in_(list(st.session_state["bulk_selection"]))).all()
            
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
                        'difficulty': q.difficulty,
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

    # QUERY
    if opec_focus:
        # Usamos el servicio de alta precisión
        questions_all = QuestionService.get_questions_for_user(
            db, u_id, include_review=is_admin_user
        )
        # Aplicamos filtros de UI sobre el set filtrado por OPEC (Filtrado en memoria Python)
        filtered = []
        for q in questions_all:
            if search and not (search.lower() in (q.stem + (q.rationale or "")).lower()):
                continue
            if track_f != "Todos" and q.track != track_f:
                continue
            if diff_f and q.difficulty not in diff_f:
                continue
            local_reports = st.session_state.get("bank_local_audit_reports", {})
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
        questions = filtered[offset:offset+PAGE_SIZE]
        if is_admin_user:
            visible_safe = sum(is_safe_for_active_study(item) for item in filtered)
            st.info(
                f"🎯 **Concurso activo:** {total_count} registros coinciden con los filtros; "
                f"{visible_safe} están habilitados para estudio."
            )
        else:
            st.info(f"🎯 **Enfoque OPEC:** {total_count} preguntas aptas para tu preparación.")
    else:
        # Búsqueda global estándar (SQL)
        query = db.query(Question).filter(Question.competition_id == competition_id)
        if search:
            query = query.filter(Question.stem.ilike(f"%{search}%") | Question.rationale.ilike(f"%{search}%"))
        if track_f != "Todos":
            query = query.filter(Question.track == track_f)
        if diff_f:
            query = query.filter(Question.difficulty.in_(diff_f))
        
        filtered = query.all()
        if not is_admin_user:
            filtered = [q for q in filtered if is_safe_for_active_study(q)]
        local_reports = st.session_state.get("bank_local_audit_reports", {})
        if quality_f == QUALITY_LOCAL_REVIEW:
            filtered = [
                q for q in filtered
                if local_reports.get(str(q.question_id), {}).get("status") == "REVIEW"
            ]
        else:
            filtered = [q for q in filtered if matches_quality_filter(q, quality_f)]
        if format_f != "Todos":
            filtered = [q for q in filtered if question_format_status(q) == format_f]
        total_count = len(filtered)
        PAGE_SIZE = 20
        st.session_state["page_num"] = min(
            st.session_state["page_num"], max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
        )
        offset = (st.session_state["page_num"] - 1) * PAGE_SIZE
        questions = filtered[offset:offset+PAGE_SIZE]
        st.info(f"📚 Mostrando **{len(questions)}** de **{total_count}** preguntas totales.")
    
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
            diff_tags = {1: "🟢", 2: "🟡", 3: "🔴"}
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
                format_icon = "TIPO EXAMEN" if format_status == OFFICIAL_LABEL else "PRÁCTICA" if format_status == PRACTICE_LABEL else "REVISAR"
                display_title = f"{status_icon} {format_icon} {diff_tags.get(q.difficulty, '⚪')} [{q.track or 'SIN EJE'}] {q.stem[:80]}..."
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
                    
                    st.markdown(f"**Respuesta Correcta:** :green[{q.correct_key}]")
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
                                    st.error(f"Error: {e}")

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
                    
                    progress = st.progress(0)
                    for index, row in df.iterrows():
                        progress.progress((index + 1) / len(df))
                        stem = str(row['stem'])
                        h = compute_hash(stem)
                        
                        if h in existing_hashes:
                            count_dupe += 1
                            continue
                            
                        ops = {
                            "A": str(row['options_A']),
                            "B": str(row['options_B']),
                            "C": str(row['options_C']),
                            "D": str(row['options_D'])
                        }
                        
                        # Safe difficulty conversion
                        raw_diff = row.get('difficulty', 2)
                        try:
                            difficulty = int(float(raw_diff)) if not pd.isna(raw_diff) else 2
                        except (ValueError, TypeError):
                            difficulty = 2
                            
                        q = Question(
                            competition_id=get_active_competition_id(db, u_id),
                            question_id=str(uuid.uuid4()),
                            track=str(row['track']).upper(),
                            competency=str(row.get('competency', 'General')),
                            topic=str(row.get('topic', 'General')),
                            difficulty=difficulty,
                            stem=stem,
                            options_json=ops,
                            correct_key=str(row['correct_key']).strip().upper(),
                            rationale=str(row.get('rationale', '')),
                            hash_norm=h
                        )
                        db.add(q)
                        count_ok += 1
                        existing_hashes.append(h) # Update local cache for batch
                    
                    db.commit()
                    st.balloons()
                    st.success(f"¡Importación Finalizada! Nuevas: {count_ok} | Duplicadas omitidas: {count_dupe}")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

elif action == "Crear manualmente":
    with st.form("manual_create"):
        st.subheader("Nueva Pregunta")
        col1, col2 = st.columns(2)
        with col1:
            track = st.selectbox("Track / Eje", ["FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"])
            topic = st.text_input("Tema")
        with col2:
            stem = st.text_area("Enunciado de la Pregunta")
            difficulty = st.select_slider("Dificultad", options=[1, 2, 3], format_func=lambda x: {1: "Básico", 2: "Intermedio", 3: "Avanzado"}[x], value=2)
            
        st.markdown("---")
        st.markdown("**Opciones de Respuesta**")
        c1, c2 = st.columns(2)
        with c1:
            op_a = st.text_input("Opción A")
            op_b = st.text_input("Opción B")
        with c2:
            op_c = st.text_input("Opción C")
            op_d = st.text_input("Opción D")
            
        col_correct, col_rationale = st.columns([1, 2])
        with col_correct:
            correct = st.selectbox("Respuesta Correcta", ["A", "B", "C", "D"])
        with col_rationale:
            rationale = st.text_area("Justificación / Explicación")
        
        if st.form_submit_button("Guardar Pregunta", type="primary"):
            h = compute_hash(stem)
            if db.query(Question).filter_by(hash_norm=h).first():
                st.error("¡Pregunta idéntica ya existe!")
            else:
                q = Question(
                    competition_id=get_active_competition_id(db, u_id),
                    question_id=str(uuid.uuid4()),
                    track=track,
                    competency="Manual",
                    topic=topic,
                    stem=stem,
                    difficulty=difficulty,
                    options_json={"A": op_a, "B": op_b, "C": op_c, "D": op_d},
                    correct_key=correct,
                    rationale=rationale,
                    hash_norm=h
                )
                db.add(q)
                db.commit()
                st.success("Pregunta guardada exitosamente.")

db.close()
