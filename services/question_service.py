import json
from sqlalchemy import inspect
from sqlalchemy.orm import selectinload

from db.models import (
    CaseStudy,
    OpecProfile,
    Question,
    QuestionOpecScope,
    UserOPEC,
)
from core.competitions import get_active_competition_id
from core.legacy_question_audit import is_safe_for_active_study
from core.question_opec_scope import question_matches_opec


SUPPORTED_BANK_PARTITIONS = frozenset({"training", "measurement", "anchor", "reserved"})


def _normalise_bank_partitions(bank_partitions):
    values = tuple(dict.fromkeys(str(value).strip() for value in bank_partitions))
    if not values or any(value not in SUPPORTED_BANK_PARTITIONS for value in values):
        raise ValueError("Partición de banco no válida.")
    return values


def _explicit_opec_question_ids(
    db,
    competition_id,
    opec_number,
    *,
    bank_partitions=("training",),
):
    """Return persisted scope IDs, or None while the additive schema is absent.

    An existing canonical profile with zero question scopes deliberately
    returns an empty set: its bank is not silently filled from text matching.
    """
    bank_partitions = _normalise_bank_partitions(bank_partitions)
    # Inspect through the Session-owned connection.  Inspecting the Engine can
    # open/close the same DBAPI connection used by SQLite ``:memory:`` and roll
    # back an in-flight learning session.
    inspector = inspect(db.connection())
    required = {"opec_profiles", "question_opec_scopes"}
    if not all(inspector.has_table(table) for table in required):
        return None
    profile = db.query(OpecProfile).filter_by(
        competition_id=competition_id,
        opec_number=str(opec_number),
    ).first()
    if profile is None:
        return None
    return {
        row[0]
        for row in db.query(QuestionOpecScope.question_id).filter(
            QuestionOpecScope.opec_profile_id == profile.id,
            QuestionOpecScope.bank_partition.in_(bank_partitions),
        ).all()
    }

class QuestionService:
    @staticmethod
    def get_questions_for_user(
        db,
        user_id,
        include_review=False,
        *,
        competition_id=None,
        user_opec=None,
        bank_partitions=("training",),
    ):
        """
        Calcula las preguntas pertinentes para el usuario basándose en su OPEC activa.
        Utiliza un motor de keywords dinámico v48.1 Mikey.
        """
        requested_partitions = _normalise_bank_partitions(bank_partitions)
        # Reserved content is an editorial holdout. It is administered only
        # through the opaque, role-gated partition service and is never a
        # question-delivery partition for an aspirant session.
        if "reserved" in requested_partitions:
            return []
        if user_opec is None:
            user_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()
        
        # El banco siempre se limita al concurso activo.
        if competition_id is None:
            competition_id = get_active_competition_id(db, user_id)
        # El plan diario analiza casos completos. Precargarlos evita una consulta
        # adicional por cada pregunta/caso al construir los bloques GOA.
        query = db.query(Question).options(
            selectinload(Question.case_study).selectinload(CaseStudy.questions)
        )
        if competition_id is not None:
            query = query.filter(Question.competition_id == competition_id)

        all_candidates = query.all()
        if not include_review:
            all_candidates = [q for q in all_candidates if is_safe_for_active_study(q)]
        
        # Sin una OPEC activa no existe un alcance seguro. Devolver todo el
        # concurso podría filtrar material de medición, anclaje o reserva.
        if not user_opec:
            return []

        # Un concurso puede contener muchas OPEC. Competition_id evita mezclar
        # concursos; este segundo filtro evita mezclar cargos dentro del mismo
        # proceso. El material sin una OPEC demostrable queda fuera hasta que se
        # clasifique de forma explícita.
        if competition_id is not None:
            explicit_ids = _explicit_opec_question_ids(
                db,
                competition_id,
                user_opec.opec_number,
                bank_partitions=requested_partitions,
            )
            if explicit_ids is not None:
                return [
                    question for question in all_candidates
                    if question.question_id in explicit_ids
                ]
            # Legacy metadata has no trustworthy concept of measurement,
            # anchor or reserved partitions.  Only training may use the
            # conservative text/identifier fallback while Phase 1 is applied.
            if requested_partitions != ("training",):
                return []
            return [
                question for question in all_candidates
                if question_matches_opec(question, user_opec.opec_number)
            ]

        # 1. Extracción de Keywords de la OPEC
        functions = user_opec.functions if isinstance(user_opec.functions, list) else []
        purpose = user_opec.purpose if user_opec.purpose else ""
        job_title = user_opec.job_title if user_opec.job_title else ""
        
        opec_text = (job_title + " " + purpose + " " + " ".join(functions)).lower()
        
        # 2. Detección de Naturaleza (Tributaria vs Aduanera)
        is_tributaria = any(w in opec_text for w in ['tributari', 'impuesto', 'renta', 'iva', 'cobro', 'recaudo'])
        is_aduanera = any(w in opec_text for w in ['aduan', 'arancel', 'import', 'export', 'tránsito', 'cabotaje', 'zona franca'])

        # 3. Aplicación de Filtros Maestro
        final_questions = []

        # [0] PRIORIDAD ABSOLUTA V50: Coincidencia Exacta de OPEC
        # Si existen preguntas "hechas a medida" para este código OPEC, ignoramos el resto.
        if user_opec.opec_number:
            strict_matches = [q for q in all_candidates if user_opec.opec_number in q.topic]
            # Si tenemos un banco decente (>10 preguntas) específico, usamos SOLO esto.
            if len(strict_matches) >= 5:
                # Opcional: Mezclar con comportamentales genéricas si se desea, 
                # pero por ahora devolvemos lo específico que es lo que pide el usuario.
                return strict_matches
        
        
        # [1] Heurística Keywords (Legacy / Fallback) - SI NO HAY MATCH EXACTO
        for q in all_candidates:
            q_text = (q.topic + " " + q.competency + " " + q.stem).lower()
            
            # A. Filtros Negativos Cruzados (Blindaje Cesar/Cualquier Usuario)
            # v6.4 Mikey: Los temas transversales (Integridad, Etica, Comportamental) NUNCA se filtran.
            is_transcendental = any(x in q_text for x in ['integridad', 'ética', 'etica', 'constitución', 'constitucion', 'comportamental', 'conductual'])
            
            if not is_transcendental:
                if is_tributaria and not is_aduanera:
                    # Si soy puramente tributario, prohibido temas de aduana (Cesar Rule)
                    forbidden = ['aduan', 'arancel', 'import', 'export', 'tráfico postal', 'cabotaje', 'zona franca']
                    if any(f in q_text for f in forbidden):
                        continue
                
                if is_aduanera and not is_tributaria:
                    # Si soy puramente aduanero, prohibido temas de recaudo tributario interno puro
                    forbidden = ['renta pbx', 'retención en la fuente', 'impuesto de consumo']
                    if any(f in q_text for f in forbidden):
                        continue

            # B. Validación de Formato GOA (Situacional + 3 Opciones)
            # Para cargos Profesionales (Nivel 1/2) somos más estrictos con el protocolo 2667
            is_behavioral = any(x in q.competency.lower() or x in q.topic.lower() for x in ['comportamental', 'conductual', 'integridad', 'valores', 'ética', 'etica'])
            
            if not is_behavioral:
                # Requerir formato situacional para preguntas técnicas (GOA 2667)
                if "SITUACIÓN" not in q.stem.upper():
                    continue
                
                # Requerir exactamente 3 opciones (Estándar CNSC 2024)
                try:
                    opts = q.options_json if isinstance(q.options_json, dict) else json.loads(q.options_json)
                    if len(opts) != 3:
                        continue
                except (TypeError, ValueError):
                    continue

            final_questions.append(q)
        
        return final_questions
