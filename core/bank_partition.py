"""Conservative administration of canonical OPEC bank partitions.

Partition changes are editorial events, not display preferences.  This module
keeps the OPEC scope and the immutable revision trail aligned, and deliberately
returns no reserved question content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from sqlalchemy import func, inspect

from core.legacy_question_audit import is_safe_for_active_study
from core.source_evidence import OFFICIAL_DOMAINS
from db.models import (
    OpecProfile,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
    SourceDocument,
    User,
    UserOPEC,
)


BANK_PARTITIONS = ("training", "measurement", "anchor", "reserved")
ASPIRANT_VISIBLE_PARTITIONS = frozenset({"training"})
RESERVED_PARTITION = "reserved"
MAX_PARTITION_BATCH = 5

REQUIRED_PARTITION_TABLES = frozenset(
    {
        "opec_profiles",
        "question_opec_scopes",
        "question_revisions",
        "question_citations",
        "source_documents",
    }
)


class BankPartitionError(ValueError):
    """Base error for a rejected partition operation."""


class BankPartitionSchemaError(BankPartitionError):
    """The additive canonical schema is not ready."""


class BankPartitionContextError(BankPartitionError):
    """The user, competition or OPEC context is ambiguous."""


class BankPartitionEligibilityError(BankPartitionError):
    """One or more questions do not pass the promotion barrier."""


@dataclass(frozen=True)
class ActiveBankContext:
    user_id: int
    user_opec_id: int
    competition_id: int
    opec_number: str
    opec_profile_id: int


@dataclass(frozen=True)
class PartitionEligibility:
    eligible: bool
    reason: str | None
    revision_id: str | None


@dataclass(frozen=True)
class PartitionItem:
    """Safe inventory metadata; reserved rows never contain topic or content."""

    question_id: str
    partition: str
    display_label: str
    eligible: bool
    blocked_reason: str | None


@dataclass(frozen=True)
class PartitionMove:
    question_id: str
    from_partition: str
    to_partition: str
    revision_id: str


def _normalise_partition(value: object) -> str:
    partition = str(value or "").strip().lower()
    if partition not in BANK_PARTITIONS:
        raise BankPartitionError("Partición de banco no válida.")
    return partition


def partition_schema_available(db) -> bool:
    schema = inspect(db.connection())
    return all(schema.has_table(table) for table in REQUIRED_PARTITION_TABLES)


def _require_schema(db) -> None:
    if not partition_schema_available(db):
        raise BankPartitionSchemaError(
            "La administración de particiones requiere completar el esquema canónico."
        )


def resolve_active_bank_context(
    db,
    *,
    user_id: int,
    competition_id: int | None = None,
) -> ActiveBankContext:
    """Resolve the most recent active OPEC inside one authenticated context."""

    _require_schema(db)
    query = db.query(UserOPEC).filter(
        UserOPEC.user_id == int(user_id),
        UserOPEC.is_active.is_(True),
    )
    if competition_id is not None:
        query = query.filter(UserOPEC.competition_id == int(competition_id))
    active_opec = query.order_by(
        UserOPEC.updated_at.desc(), UserOPEC.id.desc()
    ).first()
    if active_opec is None or active_opec.competition_id is None:
        raise BankPartitionContextError(
            "No existe una OPEC activa dentro del concurso seleccionado."
        )

    profile_rows = db.query(OpecProfile).filter(
        OpecProfile.competition_id == active_opec.competition_id,
        OpecProfile.opec_number == str(active_opec.opec_number),
    ).all()
    if len(profile_rows) != 1:
        raise BankPartitionContextError(
            "La OPEC activa no tiene un perfil canónico único."
        )
    profile = profile_rows[0]
    return ActiveBankContext(
        user_id=int(active_opec.user_id),
        user_opec_id=int(active_opec.id),
        competition_id=int(active_opec.competition_id),
        opec_number=str(active_opec.opec_number),
        opec_profile_id=int(profile.id),
    )


def partition_counts(db, *, opec_profile_id: int) -> dict[str, int]:
    """Return counts only; this API never returns reserved content."""

    _require_schema(db)
    counts = {partition: 0 for partition in BANK_PARTITIONS}
    rows = (
        db.query(QuestionOpecScope.bank_partition, func.count(QuestionOpecScope.id))
        .filter(QuestionOpecScope.opec_profile_id == int(opec_profile_id))
        .group_by(QuestionOpecScope.bank_partition)
        .all()
    )
    for partition, count in rows:
        normalised = _normalise_partition(partition)
        counts[normalised] = int(count)
    return counts


def _official_document(document: SourceDocument) -> bool:
    if str(document.validity_status or "").strip().lower() != "current":
        return False
    host = (urlparse(str(document.official_url or "").strip()).hostname or "").lower()
    return bool(host) and any(
        host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_DOMAINS
    )


def has_precise_canonical_citation(db, *, question_id: str) -> bool:
    """Require a current official source and an individually verified key anchor."""

    rows = (
        db.query(QuestionCitation, SourceDocument)
        .join(
            SourceDocument,
            SourceDocument.id == QuestionCitation.source_document_id,
        )
        .filter(QuestionCitation.question_id == str(question_id))
        .all()
    )
    for citation, document in rows:
        if not _official_document(document):
            continue
        if not bool(citation.supports_key):
            continue
        if not str(citation.locator or "").strip():
            continue
        if len(str(citation.excerpt or "").strip()) < 10:
            continue
        if citation.verified_at is None:
            continue
        if not str(citation.verified_by or "").strip():
            continue
        return True
    return False


def _latest_revision(db, question_id: str) -> QuestionRevision | None:
    return (
        db.query(QuestionRevision)
        .filter(QuestionRevision.question_id == str(question_id))
        .order_by(
            QuestionRevision.revision_number.desc(),
            QuestionRevision.created_at.desc(),
        )
        .first()
    )


def partition_eligibility(
    db,
    *,
    question: Question,
    current_partition: str,
) -> PartitionEligibility:
    """Evaluate the strict barrier without changing the question or its scope."""

    partition = _normalise_partition(current_partition)
    if not is_safe_for_active_study(question):
        return PartitionEligibility(
            False,
            "La pregunta todavía no está apta para estudio.",
            None,
        )
    revision = _latest_revision(db, str(question.question_id))
    if revision is None or revision.status != "approved":
        return PartitionEligibility(
            False,
            "Falta una revisión canónica aprobada.",
            None if revision is None else str(revision.id),
        )
    if revision.bank_partition != partition:
        return PartitionEligibility(
            False,
            "La revisión más reciente no coincide con la partición del alcance.",
            str(revision.id),
        )
    if not has_precise_canonical_citation(db, question_id=str(question.question_id)):
        return PartitionEligibility(
            False,
            "Falta una cita oficial, vigente, precisa y verificada que sustente la clave.",
            str(revision.id),
        )
    return PartitionEligibility(True, None, str(revision.id))


def list_partition_items(
    db,
    *,
    opec_profile_id: int,
    partition: str,
    limit: int = 25,
) -> tuple[PartitionItem, ...]:
    """List safe metadata for a small admin batch.

    Reserved rows are intentionally opaque: no stem, topic, options, key,
    rationale or source is returned or incorporated into their label.
    """

    _require_schema(db)
    source_partition = _normalise_partition(partition)
    safe_limit = max(1, min(int(limit), 50))
    scopes = (
        db.query(QuestionOpecScope)
        .filter(
            QuestionOpecScope.opec_profile_id == int(opec_profile_id),
            QuestionOpecScope.bank_partition == source_partition,
        )
        .order_by(QuestionOpecScope.id.asc())
        .limit(safe_limit)
        .all()
    )
    items = []
    for position, scope in enumerate(scopes, start=1):
        if source_partition == RESERVED_PARTITION:
            items.append(
                PartitionItem(
                    question_id=str(scope.question_id),
                    partition=source_partition,
                    display_label=f"Elemento reservado {position}",
                    eligible=True,
                    blocked_reason=None,
                )
            )
            continue
        question = db.get(Question, str(scope.question_id))
        if question is None:
            eligibility = PartitionEligibility(
                False,
                "La pregunta asociada no existe.",
                None,
            )
        else:
            eligibility = partition_eligibility(
                db,
                question=question,
                current_partition=source_partition,
            )
        if question is None:
            display_label = f"Registro sin pregunta · {str(scope.question_id)[:8]}"
        else:
            topic = str(question.topic or "Sin tema").strip()
            display_label = f"{topic} · {str(question.question_id)[:8]}"
        items.append(
            PartitionItem(
                question_id=str(scope.question_id),
                partition=source_partition,
                display_label=display_label,
                eligible=eligibility.eligible,
                blocked_reason=eligibility.reason,
            )
        )
    return tuple(items)


def _normalise_question_ids(question_ids: Iterable[object]) -> tuple[str, ...]:
    values = tuple(str(value or "").strip() for value in question_ids)
    if not values or any(not value for value in values):
        raise BankPartitionError("Selecciona al menos una pregunta válida.")
    if len(values) > MAX_PARTITION_BATCH:
        raise BankPartitionError(
            f"Cada movimiento admite máximo {MAX_PARTITION_BATCH} preguntas."
        )
    if len(values) != len(set(values)):
        raise BankPartitionError("La selección contiene preguntas duplicadas.")
    return values


def move_question_partitions(
    db,
    *,
    context: ActiveBankContext,
    question_ids: Iterable[object],
    from_partition: str,
    to_partition: str,
    actor: str,
    reason: str,
) -> tuple[PartitionMove, ...]:
    """Atomically preflight and stage an explicit, revision-backed movement."""

    _require_schema(db)
    source_partition = _normalise_partition(from_partition)
    target_partition = _normalise_partition(to_partition)
    if source_partition == target_partition:
        raise BankPartitionError("La partición de origen y destino deben ser distintas.")
    ids = _normalise_question_ids(question_ids)
    clean_actor = str(actor or "").strip()
    clean_reason = str(reason or "").strip()
    if not clean_actor:
        raise BankPartitionError("El movimiento requiere identificar al administrador.")
    if len(clean_reason) < 8:
        raise BankPartitionError("Registra un motivo editorial de al menos 8 caracteres.")

    if not isinstance(context, ActiveBankContext):
        raise BankPartitionContextError("El movimiento requiere el contexto OPEC activo.")
    active_opec = db.get(UserOPEC, int(context.user_opec_id))
    profile = db.get(OpecProfile, int(context.opec_profile_id))
    administrator = db.get(User, int(context.user_id))
    if (
        administrator is None
        or str(administrator.role or "").strip().lower() != "admin"
    ):
        raise BankPartitionContextError(
            "Solo un administrador autenticado puede mover particiones."
        )
    administrator_identities = {
        str(value or "").strip().casefold()
        for value in (administrator.username, administrator.email)
        if str(value or "").strip()
    }
    if clean_actor.casefold() not in administrator_identities:
        raise BankPartitionContextError(
            "La identidad de auditoría no coincide con el administrador autenticado."
        )
    current_active = None
    if active_opec is not None and active_opec.user_id is not None:
        current_active = (
            db.query(UserOPEC)
            .filter(
                UserOPEC.user_id == active_opec.user_id,
                UserOPEC.is_active.is_(True),
            )
            .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
            .first()
        )
    if (
        active_opec is None
        or profile is None
        or active_opec.user_id != context.user_id
        or current_active is None
        or current_active.id != active_opec.id
        or not bool(active_opec.is_active)
        or active_opec.competition_id != context.competition_id
        or profile.competition_id != context.competition_id
        or str(active_opec.opec_number) != context.opec_number
        or str(profile.opec_number) != context.opec_number
    ):
        raise BankPartitionContextError(
            "La OPEC activa cambió; recarga la vista antes de mover el banco."
        )

    scopes = (
        db.query(QuestionOpecScope)
        .filter(
            QuestionOpecScope.opec_profile_id == int(context.opec_profile_id),
            QuestionOpecScope.question_id.in_(ids),
        )
        .with_for_update()
        .all()
    )
    scopes_by_question: dict[str, list[QuestionOpecScope]] = {}
    for scope in scopes:
        scopes_by_question.setdefault(str(scope.question_id), []).append(scope)
    missing_or_duplicate = [
        question_id
        for question_id in ids
        if len(scopes_by_question.get(question_id, ())) != 1
    ]
    if missing_or_duplicate:
        raise BankPartitionContextError(
            "Cada pregunta debe tener exactamente un alcance en la OPEC activa."
        )

    cross_scope_counts = dict(
        db.query(QuestionOpecScope.question_id, func.count(QuestionOpecScope.id))
        .filter(QuestionOpecScope.question_id.in_(ids))
        .group_by(QuestionOpecScope.question_id)
        .all()
    )
    if any(int(cross_scope_counts.get(question_id, 0)) != 1 for question_id in ids):
        raise BankPartitionContextError(
            "Una pregunta con alcances OPEC compartidos requiere revisión coordinada; "
            "no se moverá desde esta vista."
        )

    prepared = []
    eligibility_errors = []
    for question_id in ids:
        scope = scopes_by_question[question_id][0]
        if scope.bank_partition != source_partition:
            raise BankPartitionContextError(
                "La partición de origen cambió; recarga el inventario antes de continuar."
            )
        question = db.get(Question, question_id)
        if question is None or question.competition_id != profile.competition_id:
            raise BankPartitionContextError(
                "La pregunta no pertenece al concurso de la OPEC activa."
            )
        eligibility = partition_eligibility(
            db,
            question=question,
            current_partition=source_partition,
        )
        if not eligibility.eligible:
            eligibility_errors.append(eligibility.reason or "No apta.")
            continue
        revision = db.get(QuestionRevision, eligibility.revision_id)
        if revision is None:
            eligibility_errors.append("No se encontró la revisión aprobada.")
            continue
        prepared.append((scope, revision))
    if eligibility_errors:
        unique_reasons = "; ".join(dict.fromkeys(eligibility_errors))
        raise BankPartitionEligibilityError(
            f"El lote no cumple la barrera editorial: {unique_reasons}"
        )

    moves = []
    for scope, revision in prepared:
        next_number = int(
            db.query(func.max(QuestionRevision.revision_number))
            .filter(QuestionRevision.question_id == str(scope.question_id))
            .scalar()
            or 0
        ) + 1
        movement_revision = QuestionRevision(
            question_id=str(scope.question_id),
            revision_number=next_number,
            content_hash=revision.content_hash,
            stem=revision.stem,
            options_json=dict(revision.options_json or {}),
            correct_key=revision.correct_key,
            rationale=revision.rationale,
            distractor_explanations=(
                dict(revision.distractor_explanations)
                if isinstance(revision.distractor_explanations, dict)
                else revision.distractor_explanations
            ),
            subtopic=revision.subtopic,
            cognitive_level=revision.cognitive_level,
            difficulty_level=revision.difficulty_level,
            bank_partition=target_partition,
            source_snapshot=(
                dict(revision.source_snapshot)
                if isinstance(revision.source_snapshot, dict)
                else revision.source_snapshot
            ),
            status="approved",
            change_reason=(
                f"Movimiento de partición {source_partition} → "
                f"{target_partition}: {clean_reason}"
            ),
            actor=clean_actor,
            actor_type="admin_partition_move",
        )
        db.add(movement_revision)
        scope.bank_partition = target_partition
        db.flush()
        moves.append(
            PartitionMove(
                question_id=str(scope.question_id),
                from_partition=source_partition,
                to_partition=target_partition,
                revision_id=str(movement_revision.id),
            )
        )

    remaining_scope_count = (
        db.query(func.count(QuestionOpecScope.id))
        .filter(
            QuestionOpecScope.opec_profile_id == int(context.opec_profile_id),
            QuestionOpecScope.question_id.in_(ids),
        )
        .scalar()
    )
    if int(remaining_scope_count or 0) != len(ids):
        raise BankPartitionContextError(
            "El movimiento dejaría alcances duplicados o incompletos."
        )
    return tuple(moves)
