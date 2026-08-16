from __future__ import annotations
import datetime
import uuid
import sys
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, registry

# --- EL EXORCISMO TOTAL v19.0 - MIKEY ---
# FORCE DEPLOY v20 - User reported Import Error, assuming stale cache.
# Forzamos que la CLASE BASE sea un objeto único global en el proceso de Python.
# Esto es más agresivo que solo compartir el registry.
BASE_KEY = "_mikey_sqlalchemy_base_v19"

if not hasattr(sys, BASE_KEY):
    class Base(DeclarativeBase):
        pass
    setattr(sys, BASE_KEY, Base)
    print(f"🔨 [DB_MODELS] Clase Base v19 Creada y Anclada en sys. Mikey", file=sys.stderr)
else:
    Base = getattr(sys, BASE_KEY)
    print(f"♻️ [DB_MODELS] Clase Base v19 Recuperada de sys. Mikey", file=sys.stderr)

# --- CLASES ---
# Nota: Definimos las clases en un orden que facilite la resolución de strings de SQLAlchemy.

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="user")
    
    # --- Suscripciones mikey v4.0 ---
    subscription_tier: Mapped[str] = mapped_column(String, default="free")  # free | pro
    subscription_expiry: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    opecs: Mapped[List["UserOPEC"]] = relationship("UserOPEC", back_populates="user", cascade="all, delete-orphan")
    performance: Mapped[List["QuestionPerformance"]] = relationship("QuestionPerformance", back_populates="user", cascade="all, delete-orphan")
    stats: Mapped[Optional["UserStats"]] = relationship("UserStats", back_populates="user", cascade="all, delete-orphan")
    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["Achievement"]] = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[List["Skill"]] = relationship("Skill", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[List["UserAPIKey"]] = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")
    ethics_attempts: Mapped[List["EthicsAttempt"]] = relationship("EthicsAttempt", back_populates="user", cascade="all, delete-orphan")

class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    entity: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class OpecProfile(Base):
    """Identidad canónica de una OPEC dentro de un concurso.

    ``UserOPEC`` se conserva como configuración histórica por usuario. Esta tabla
    representa la ficha compartida del empleo y permite que el banco declare su
    alcance sin asumir que todas las OPEC de un concurso son equivalentes.
    """

    __tablename__ = "opec_profiles"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "opec_number",
            name="uq_opec_profile_competition_number",
        ),
        Index("ix_opec_profile_number", "opec_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(250))
    level: Mapped[Optional[str]] = mapped_column(String(100))
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    functions: Mapped[Optional[dict]] = mapped_column(JSON)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    source_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_verification",
    )
    source_version: Mapped[Optional[str]] = mapped_column(String(100))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )


class OpecSimulationPolicy(Base):
    """Versioned simulator configuration for one canonical OPEC.

    Product defaults and parameters evidenced by an official publication live
    in separate columns.  A provisional practice value must never be copied
    into an ``official_*`` field merely because the application uses it.
    """

    __tablename__ = "opec_simulation_policies"
    __table_args__ = (
        UniqueConstraint(
            "opec_profile_id",
            "version_number",
            name="uq_opec_simulation_policy_version_number",
        ),
        UniqueConstraint(
            "opec_profile_id",
            "policy_version",
            name="uq_opec_simulation_policy_version_label",
        ),
        UniqueConstraint(
            "opec_profile_id",
            "active_slot",
            name="uq_opec_simulation_policy_one_active",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_opec_simulation_policy_version_number",
        ),
        CheckConstraint(
            "policy_status IN ('draft', 'provisional', 'verified', 'retired')",
            name="ck_opec_simulation_policy_status",
        ),
        CheckConstraint(
            "official_source_status IS NULL OR official_source_status IN ("
            "'unpublished', 'pending_verification', 'partial', "
            "'verified_current', 'superseded')",
            name="ck_opec_simulation_policy_source_status",
        ),
        CheckConstraint(
            "internal_navigation_mode IN ('sequential', 'free', 'case_locked')",
            name="ck_opec_simulation_policy_internal_navigation",
        ),
        CheckConstraint(
            "official_navigation_mode IS NULL OR official_navigation_mode IN ("
            "'sequential', 'free', 'case_locked')",
            name="ck_opec_simulation_policy_official_navigation",
        ),
        CheckConstraint(
            "internal_diagnostic_questions >= 1 AND "
            "internal_diagnostic_questions <= internal_short_questions AND "
            "internal_short_questions <= internal_partial_questions AND "
            "internal_partial_questions <= internal_full_questions AND "
            "internal_full_questions <= 5000",
            name="ck_opec_simulation_policy_mode_counts",
        ),
        CheckConstraint(
            "internal_minutes_per_question > 0 AND "
            "internal_minutes_per_question <= 60",
            name="ck_opec_simulation_policy_minutes_per_question",
        ),
        CheckConstraint(
            "internal_max_questions_per_case >= 1 AND "
            "internal_max_questions_per_case <= 10",
            name="ck_opec_simulation_policy_questions_per_case",
        ),
        CheckConstraint(
            "official_question_count IS NULL OR "
            "(official_question_count >= 1 AND official_question_count <= 5000)",
            name="ck_opec_simulation_policy_official_questions",
        ),
        CheckConstraint(
            "official_duration_minutes IS NULL OR "
            "(official_duration_minutes >= 1 AND official_duration_minutes <= 1440)",
            name="ck_opec_simulation_policy_official_duration",
        ),
        CheckConstraint(
            "official_minutes_per_question IS NULL OR "
            "(official_minutes_per_question > 0 AND official_minutes_per_question <= 60)",
            name="ck_opec_simulation_policy_official_minutes_per_question",
        ),
        CheckConstraint(
            "official_max_questions_per_case IS NULL OR "
            "(official_max_questions_per_case >= 1 AND "
            "official_max_questions_per_case <= 10)",
            name="ck_opec_simulation_policy_official_questions_per_case",
        ),
        CheckConstraint(
            "(official_question_count IS NULL AND "
            "official_duration_minutes IS NULL AND "
            "official_minutes_per_question IS NULL AND "
            "official_max_questions_per_case IS NULL AND "
            "official_navigation_mode IS NULL AND "
            "official_composition_json IS NULL AND "
            "official_weights_json IS NULL) OR ("
            "official_source_url IS NOT NULL AND "
            "official_source_version IS NOT NULL AND "
            "official_source_status IN ('pending_verification', 'partial', "
            "'verified_current', 'superseded'))",
            name="ck_opec_simulation_policy_official_provenance",
        ),
        CheckConstraint(
            "policy_status != 'verified' OR ("
            "official_source_url IS NOT NULL AND "
            "official_source_version IS NOT NULL AND "
            "official_source_status = 'verified_current' AND "
            "official_verified_at IS NOT NULL AND ("
            "official_question_count IS NOT NULL OR "
            "official_duration_minutes IS NOT NULL OR "
            "official_minutes_per_question IS NOT NULL OR "
            "official_max_questions_per_case IS NOT NULL OR "
            "official_navigation_mode IS NOT NULL OR "
            "official_composition_json IS NOT NULL OR "
            "official_weights_json IS NOT NULL))",
            name="ck_opec_simulation_policy_verified_source",
        ),
        CheckConstraint(
            "(is_active AND active_slot = 1 AND policy_status != 'retired') OR "
            "(NOT is_active AND active_slot IS NULL)",
            name="ck_opec_simulation_policy_active_slot",
        ),
        Index(
            "ix_opec_simulation_policy_context_active",
            "competition_id",
            "opec_profile_id",
            "is_active",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opec_profile_id: Mapped[int] = mapped_column(
        ForeignKey("opec_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    supersedes_policy_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("opec_simulation_policies.id", ondelete="RESTRICT"), index=True
    )
    policy_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="provisional"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Portable one-active-row invariant: UNIQUE allows many NULL retired slots
    # in both SQLite and PostgreSQL, but only one profile row can hold slot 1.
    active_slot: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    # Editable product configuration. These values are always internal.
    internal_diagnostic_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=9
    )
    internal_short_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    internal_partial_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    internal_full_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    internal_minutes_per_question: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.0
    )
    internal_max_questions_per_case: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    internal_navigation_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sequential"
    )
    internal_composition_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"functional": 1.0}
    )
    internal_weights_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"functional": 1.0}
    )

    # Official parameters remain NULL until a cited publication establishes
    # them for this OPEC/process. Presence never follows from internal defaults.
    official_question_count: Mapped[Optional[int]] = mapped_column(Integer)
    official_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    official_minutes_per_question: Mapped[Optional[float]] = mapped_column(Float)
    official_max_questions_per_case: Mapped[Optional[int]] = mapped_column(Integer)
    official_navigation_mode: Mapped[Optional[str]] = mapped_column(String(30))
    official_composition_json: Mapped[Optional[dict]] = mapped_column(
        JSON(none_as_null=True)
    )
    official_weights_json: Mapped[Optional[dict]] = mapped_column(
        JSON(none_as_null=True)
    )
    official_source_title: Mapped[Optional[str]] = mapped_column(String(300))
    official_source_url: Mapped[Optional[str]] = mapped_column(Text)
    official_source_version: Mapped[Optional[str]] = mapped_column(String(150))
    official_source_status: Mapped[Optional[str]] = mapped_column(String(40))
    official_published_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    official_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    change_reason: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

class UserOPEC(Base):
    __tablename__ = "user_opec"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    opec_number: Mapped[str] = mapped_column(String)
    job_title: Mapped[str] = mapped_column(String)
    level: Mapped[Optional[str]] = mapped_column(String)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    functions: Mapped[Optional[dict]] = mapped_column(JSON)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="opecs")

class StudyPlanConfig(Base):
    __tablename__ = "study_plan_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    exam_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=30)
    saturday_minutes: Mapped[int] = mapped_column(Integer, default=60)
    study_days: Mapped[list] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4, 5])
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class CaseStudy(Base):
    __tablename__ = "case_studies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    title: Mapped[Optional[str]] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    topic: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="case_study", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    question_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    case_id: Mapped[Optional[str]] = mapped_column(ForeignKey("case_studies.id"))
    track: Mapped[str] = mapped_column(String)
    competency: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    macro_dominio: Mapped[Optional[str]] = mapped_column(String)
    micro_competencia: Mapped[Optional[str]] = mapped_column(String)
    difficulty: Mapped[int] = mapped_column(Integer)
    question_type: Mapped[str] = mapped_column(String, default="SITUATIONAL")  # SITUATIONAL | LIKERT
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[dict] = mapped_column(JSON)
    correct_key: Mapped[Optional[str]] = mapped_column(String)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    source_refs: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    hash_norm: Mapped[str] = mapped_column(String, unique=True)
    
    # --- v32 Quality Control & Global Psychometrics Mikey ---
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_report: Mapped[Optional[dict]] = mapped_column(JSON)
    global_hits: Mapped[int] = mapped_column(Integer, default=0)
    global_misses: Mapped[int] = mapped_column(Integer, default=0)

    case_study: Mapped[Optional["CaseStudy"]] = relationship("CaseStudy", back_populates="questions")
    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="question")
    perf_entries: Mapped[List["QuestionPerformance"]] = relationship("QuestionPerformance", back_populates="question")
    anki_enrichment: Mapped[Optional["QuestionAnkiEnrichment"]] = relationship(
        "QuestionAnkiEnrichment",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
    )


class QuestionOpecScope(Base):
    """Alcance OPEC explícito de una pregunta.

    La ausencia de esta asociación significa "sin alcance demostrado", no
    "pertenece a la OPEC activa".
    """

    __tablename__ = "question_opec_scopes"
    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "opec_profile_id",
            name="uq_question_opec_scope",
        ),
        CheckConstraint(
            "function_number IS NULL OR "
            "(function_number >= 1 AND function_number <= 100)",
            name="ck_question_opec_scope_function",
        ),
        CheckConstraint(
            "scope_kind IN ('primary', 'shared', 'transversal')",
            name="ck_question_opec_scope_kind",
        ),
        CheckConstraint(
            "bank_partition IN ('training', 'measurement', 'anchor', 'reserved')",
            name="ck_question_opec_scope_partition",
        ),
        Index(
            "ix_question_opec_scope_profile_function",
            "opec_profile_id",
            "function_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opec_profile_id: Mapped[int] = mapped_column(
        ForeignKey("opec_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    function_number: Mapped[Optional[int]] = mapped_column(Integer)
    scope_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="primary",
    )
    bank_partition: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="training",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class CaseOpecScope(Base):
    """Alcance OPEC explícito de un caso situacional."""

    __tablename__ = "case_opec_scopes"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "opec_profile_id",
            name="uq_case_opec_scope",
        ),
        CheckConstraint(
            "function_number IS NULL OR "
            "(function_number >= 1 AND function_number <= 100)",
            name="ck_case_opec_scope_function",
        ),
        CheckConstraint(
            "scope_kind IN ('primary', 'shared', 'transversal')",
            name="ck_case_opec_scope_kind",
        ),
        Index(
            "ix_case_opec_scope_profile_function",
            "opec_profile_id",
            "function_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opec_profile_id: Mapped[int] = mapped_column(
        ForeignKey("opec_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    function_number: Mapped[Optional[int]] = mapped_column(Integer)
    scope_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="primary",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class SourceDocument(Base):
    """Documento oficial o guía que puede sustentar una pregunta."""

    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("document_key", name="uq_source_document_key"),
        CheckConstraint(
            "validity_status IN "
            "('pending', 'current', 'superseded', 'repealed', 'unknown')",
            name="ck_source_document_validity",
        ),
        Index("ix_source_document_entity_type", "entity", "document_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_key: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    entity: Mapped[Optional[str]] = mapped_column(String(200))
    document_type: Mapped[Optional[str]] = mapped_column(String(100))
    official_url: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[Optional[str]] = mapped_column(String(100))
    issued_at: Mapped[Optional[datetime.date]] = mapped_column(Date)
    valid_from: Mapped[Optional[datetime.date]] = mapped_column(Date)
    valid_until: Mapped[Optional[datetime.date]] = mapped_column(Date)
    validity_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    last_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )


class QuestionCitation(Base):
    """Ancla verificable entre una pregunta y una ubicación de una fuente."""

    __tablename__ = "question_citations"
    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "source_document_id",
            "locator",
            name="uq_question_citation_locator",
        ),
        Index(
            "ix_question_citation_question_verified",
            "question_id",
            "verified_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    locator: Mapped[str] = mapped_column(String(250), nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text)
    supports_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    verified_by: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class QuestionRevision(Base):
    """Instantánea inmutable de una versión revisada de una pregunta."""

    __tablename__ = "question_revisions"
    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "revision_number",
            name="uq_question_revision_number",
        ),
        CheckConstraint("revision_number >= 1", name="ck_question_revision_number"),
        CheckConstraint(
            "status IN ('candidate', 'approved', 'retired', 'quarantined')",
            name="ck_question_revision_status",
        ),
        CheckConstraint(
            "bank_partition IN ('training', 'measurement', 'anchor', 'reserved')",
            name="ck_question_revision_partition",
        ),
        CheckConstraint(
            "difficulty_level IS NULL OR "
            "(difficulty_level >= 1 AND difficulty_level <= 10)",
            name="ck_question_revision_difficulty",
        ),
        Index("ix_question_revision_question_status", "question_id", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Likert comportamental/integridad has no correct answer; functional PJS does.
    correct_key: Mapped[Optional[str]] = mapped_column(String(10))
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    distractor_explanations: Mapped[Optional[dict]] = mapped_column(JSON)
    subtopic: Mapped[Optional[str]] = mapped_column(String(250))
    cognitive_level: Mapped[Optional[str]] = mapped_column(String(50))
    difficulty_level: Mapped[Optional[int]] = mapped_column(Integer)
    bank_partition: Mapped[str] = mapped_column(
        String(20), nullable=False, default="training"
    )
    source_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="candidate",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[Optional[str]] = mapped_column(String(150))
    actor_type: Mapped[Optional[str]] = mapped_column(String(30))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class QuestionAnkiEnrichment(Base):
    __tablename__ = "question_anki_enrichments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    rule: Mapped[Optional[str]] = mapped_column(Text)
    exception: Mapped[Optional[str]] = mapped_column(Text)
    distractor: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    generated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="anki_enrichment")

class Attempt(Base):
    __tablename__ = "attempts"
    attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.question_id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    chosen_key: Mapped[str] = mapped_column(String)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    time_sec: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    question: Mapped["Question"] = relationship("Question", back_populates="attempts")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="attempts")

class UserStats(Base):
    __tablename__ = "user_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    max_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # --- Límites IA mikey v4.0 ---
    last_ia_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime) # Store as date part
    ia_count_today: Mapped[int] = mapped_column(Integer, default=0)
    
    last_activity: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="stats")

class Achievement(Base):
    __tablename__ = "achievements"
    achievement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    icon: Mapped[Optional[str]] = mapped_column(String)
    unlocked_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="achievements")

class Skill(Base):
    __tablename__ = "skills"
    skill_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    track: Mapped[str] = mapped_column(String)
    competency: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    macro_dominio: Mapped[Optional[str]] = mapped_column(String)
    micro_competencia: Mapped[Optional[str]] = mapped_column(String)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_weight: Mapped[float] = mapped_column(Float, default=1.0)
    last_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="skills")

class QuestionPerformance(Base):
    __tablename__ = "question_performance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.question_id"))
    hits: Mapped[int] = mapped_column(Integer, default=0)
    misses: Mapped[int] = mapped_column(Integer, default=0)
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0)
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    last_attempt: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    next_review: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    review_interval_days: Mapped[float] = mapped_column(Float, default=0.0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0)
    last_confidence: Mapped[Optional[str]] = mapped_column(String(20))
    last_error_type: Mapped[Optional[str]] = mapped_column(String(50))
    last_reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="performance")
    question: Mapped["Question"] = relationship("Question", back_populates="perf_entries")


class LearningSession(Base):
    """Sesión adaptativa que selecciona una pregunta después de cada respuesta."""

    __tablename__ = "learning_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    current_question_id: Mapped[Optional[str]] = mapped_column(ForeignKey("questions.question_id"))
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    target_minutes: Mapped[int] = mapped_column(Integer, default=20)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)


class LearningAttempt(Base):
    """Intento enriquecido de una sesión de aprendizaje."""

    __tablename__ = "learning_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.question_id"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(20))
    error_type: Mapped[Optional[str]] = mapped_column(String(40))
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())


class TopicMastery(Base):
    """Dominio agregado por usuario, concurso y tema estable."""

    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "competition_id", "topic_id", name="uq_topic_mastery_scope"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    competition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitions.id"), index=True)
    topic_id: Mapped[str] = mapped_column(String(64), index=True)
    topic_label: Mapped[str] = mapped_column(String(250))
    competency: Mapped[Optional[str]] = mapped_column(String(250))
    track: Mapped[Optional[str]] = mapped_column(String(100))
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    partial_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    next_review_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class OpecLearningSession(Base):
    """Versioned learning evidence scoped to one configured OPEC.

    This table is deliberately additive.  Legacy ``LearningSession`` rows keep
    their current meaning while new Phase 2 flows can persist the exact policy,
    blueprint and bank partition used to produce a score.
    """

    __tablename__ = "opec_learning_sessions"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('diagnostic', 'training', 'measurement', 'review')",
            name="ck_opec_learning_session_mode",
        ),
        CheckConstraint(
            "bank_partition IN ('training', 'measurement', 'anchor', 'reserved')",
            name="ck_opec_learning_session_partition",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'abandoned', 'invalid')",
            name="ck_opec_learning_session_status",
        ),
        CheckConstraint(
            "total_questions >= 0 AND answered_questions >= 0 "
            "AND answered_questions <= total_questions",
            name="ck_opec_learning_session_counts",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_opec_learning_session_score",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_opec_learning_session_timestamps",
        ),
        CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL",
            name="ck_opec_learning_session_completion",
        ),
        Index(
            "ix_opec_learning_session_context",
            "user_id",
            "competition_id",
            "user_opec_id",
            "started_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_opec_id: Mapped[int] = mapped_column(
        ForeignKey("user_opec.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Immutable identity snapshot; UserOPEC may later be renamed or deactivated.
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    blueprint_version: Mapped[Optional[str]] = mapped_column(String(100))
    bank_partition: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[Optional[float]] = mapped_column(Float)
    feedback_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    aids_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    question_revision_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    case_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    coverage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[List["OpecLearningEvent"]] = relationship(
        "OpecLearningEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OpecLearningEvent(Base):
    """One immutable answer event with the evidence visible at answer time."""

    __tablename__ = "opec_learning_events"
    __table_args__ = (
        CheckConstraint(
            "time_sec IS NULL OR time_sec >= 0",
            name="ck_opec_learning_event_time",
        ),
        CheckConstraint(
            "editorial_difficulty >= 1 AND editorial_difficulty <= 10",
            name="ck_opec_learning_event_difficulty",
        ),
        CheckConstraint(
            "function_number IS NULL OR "
            "(function_number >= 1 AND function_number <= 100)",
            name="ck_opec_learning_event_function",
        ),
        CheckConstraint(
            "novelty IN ('new', 'seen', 'repeated', 'transfer', 'unknown')",
            name="ck_opec_learning_event_novelty",
        ),
        Index("ix_opec_learning_event_session_time", "session_id", "created_at"),
        Index("ix_opec_learning_event_user_topic", "user_id", "topic_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("opec_learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("case_studies.id", ondelete="RESTRICT"), index=True
    )
    question_revision_id: Mapped[str] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    function_number: Mapped[Optional[int]] = mapped_column(Integer)
    topic_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic_label: Mapped[str] = mapped_column(String(250), nullable=False)
    # Likert/autoreport items intentionally persist NULL instead of a false key.
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    confidence: Mapped[Optional[str]] = mapped_column(String(20))
    time_sec: Mapped[Optional[int]] = mapped_column(Integer)
    novelty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    editorial_difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    source_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    source_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    evidence_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    session: Mapped["OpecLearningSession"] = relationship(
        "OpecLearningSession", back_populates="events"
    )


class OpecTopicState(Base):
    """Mastery isolated by user, competition, configured OPEC and topic."""

    __tablename__ = "opec_topic_states"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competition_id",
            "user_opec_id",
            "topic_id",
            name="uq_opec_topic_state_scope",
        ),
        CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 100",
            name="ck_opec_topic_state_mastery",
        ),
        CheckConstraint(
            "evidence_count >= 0",
            name="ck_opec_topic_state_evidence_count",
        ),
        CheckConstraint(
            "function_number IS NULL OR "
            "(function_number >= 1 AND function_number <= 100)",
            name="ck_opec_topic_state_function",
        ),
        Index(
            "ix_opec_topic_state_context_mastery",
            "user_id",
            "competition_id",
            "user_opec_id",
            "mastery_score",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_opec_id: Mapped[int] = mapped_column(
        ForeignKey("user_opec.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic_label: Mapped[str] = mapped_column(String(250), nullable=False)
    function_number: Mapped[Optional[int]] = mapped_column(Integer)
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    next_review_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, index=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class OpecStudyPlan(Base):
    """One editable study policy per user and configured OPEC."""

    __tablename__ = "opec_study_plans"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competition_id",
            "user_opec_id",
            name="uq_opec_study_plan_scope",
        ),
        CheckConstraint(
            "target_score >= 0 AND target_score <= 100",
            name="ck_opec_study_plan_target",
        ),
        CheckConstraint(
            "weekday_minutes >= 0 AND weekday_minutes <= 1440 "
            "AND saturday_minutes >= 0 AND saturday_minutes <= 1440",
            name="ck_opec_study_plan_minutes",
        ),
        Index(
            "ix_opec_study_plan_context",
            "user_id",
            "competition_id",
            "user_opec_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_opec_id: Mapped[int] = mapped_column(
        ForeignKey("user_opec.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_score: Mapped[float] = mapped_column(Float, nullable=False, default=85.0)
    exam_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    weekday_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    saturday_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    study_days: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: [0, 1, 2, 3, 4, 5]
    )
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    activities: Mapped[List["StudyActivity"]] = relationship(
        "StudyActivity",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class StudyActivity(Base):
    """A schedulable, source-linked unit of work in an OPEC study plan."""

    __tablename__ = "study_activities"
    __table_args__ = (
        CheckConstraint(
            "minutes >= 1 AND minutes <= 1440",
            name="ck_study_activity_minutes",
        ),
        CheckConstraint(
            "activity_type IN ("
            "'active_recall', 'directed_reading', 'rule', 'exception', "
            "'work_case', 'situational_questions', 'error_review', "
            "'spaced_review', 'simulation'"
            ")",
            name="ck_study_activity_type",
        ),
        CheckConstraint(
            "status IN ('planned', 'completed', 'deferred')",
            name="ck_study_activity_status",
        ),
        CheckConstraint(
            "function_number IS NULL OR "
            "(function_number >= 1 AND function_number <= 100)",
            name="ck_study_activity_function",
        ),
        CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL",
            name="ck_study_activity_completion",
        ),
        Index(
            "ix_study_activity_plan_schedule",
            "plan_id",
            "scheduled_date",
            "status",
        ),
        Index("ix_study_activity_source", "source_document_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("opec_study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    function_number: Mapped[Optional[int]] = mapped_column(Integer)
    topic_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    topic_label: Mapped[Optional[str]] = mapped_column(String(250))
    source_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), index=True
    )
    source_locator: Mapped[Optional[str]] = mapped_column(String(250))
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    plan: Mapped["OpecStudyPlan"] = relationship(
        "OpecStudyPlan", back_populates="activities"
    )


class ErrorEpisode(Base):
    """Auditable error notebook entry and its later transfer evidence."""

    __tablename__ = "error_episodes"
    __table_args__ = (
        UniqueConstraint("learning_event_id", name="uq_error_episode_event"),
        CheckConstraint(
            "category IN ("
            "'norm_unknown', 'concept_confusion', 'interpretation', "
            "'missed_exception', 'rushed_reading', 'time_management', "
            "'unjustified_answer_change', 'confidence_miscalibration', "
            "'attractive_distractor', 'forgetting'"
            ")",
            name="ck_error_episode_category",
        ),
        CheckConstraint(
            "status IN ("
            "'open', 'scheduled', 'in_progress', 'transfer_pending', "
            "'overcome', 'dismissed'"
            ")",
            name="ck_error_episode_status",
        ),
        CheckConstraint(
            "transfer_event_id IS NULL OR transfer_event_id != learning_event_id",
            name="ck_error_episode_distinct_transfer",
        ),
        CheckConstraint(
            "status != 'overcome' OR "
            "(transfer_event_id IS NOT NULL AND overcome_at IS NOT NULL)",
            name="ck_error_episode_overcome_evidence",
        ),
        Index(
            "ix_error_episode_context_status",
            "user_id",
            "competition_id",
            "user_opec_id",
            "status",
        ),
        Index("ix_error_episode_next_review", "next_review_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    learning_event_id: Mapped[str] = mapped_column(
        ForeignKey("opec_learning_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_opec_id: Mapped[int] = mapped_column(
        ForeignKey("user_opec.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opec_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.question_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    question_revision_id: Mapped[str] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    user_reasoning: Mapped[Optional[str]] = mapped_column(Text)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    rule_to_remember: Mapped[Optional[str]] = mapped_column(Text)
    source_reference: Mapped[Optional[dict]] = mapped_column(JSON)
    micro_lesson: Mapped[Optional[str]] = mapped_column(Text)
    reinforcement_question_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    next_review_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    transfer_event_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("opec_learning_events.id", ondelete="RESTRICT"), index=True
    )
    transfer_evidence: Mapped[Optional[dict]] = mapped_column(JSON)
    overcome_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class AICallLog(Base):
    """Telemetría mínima de IA; nunca almacena prompts ni secretos."""

    __tablename__ = "ai_call_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(30))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

class Configuration(Base):
    __tablename__ = "configurations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_name: Mapped[str] = mapped_column(String, unique=True)
    value: Mapped[str] = mapped_column(String)

class NormativaChunk(Base):
    __tablename__ = "normativa_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_file: Mapped[str] = mapped_column(String)
    page: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    hash_content: Mapped[str] = mapped_column(String, unique=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String)
    encrypted_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

class EthicsAttempt(Base):
    """Almacena intentos del usuario en el módulo de Ética e Integridad"""
    __tablename__ = "ethics_attempts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    categoria: Mapped[str] = mapped_column(String)  # Conflicto de Intereses, etc.
    afirmacion: Mapped[str] = mapped_column(Text)  # La afirmación presentada
    respuesta_usuario: Mapped[int] = mapped_column(Integer)  # GOA actual: 1-4; histÃ³rico: 1-5
    respuesta_esperada: Mapped[Optional[int]] = mapped_column(Integer)  # Solo intentos histÃ³ricos
    es_correcta: Mapped[Optional[bool]] = mapped_column(Boolean)  # Si la respuesta fue correcta
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)  # Si fue generada con IA
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    
    # Relación
    user: Mapped["User"] = relationship("User", back_populates="ethics_attempts")

print("✅ [DB_MODELS] Modelos exorcizados y registrados en v19. Mikey.", file=sys.stderr)
# Forzamos configuración inmediata para detectar errores de resolución de nombres
from sqlalchemy.orm import configure_mappers
try:
    configure_mappers()
    print("✨ [DB_MODELS] Mappers configurados exitosamente. Mikey.", file=sys.stderr)
except Exception as e:
    print(
        f"🔥 [DB_MODELS] Error en configuración de mappers: {type(e).__name__}",
        file=sys.stderr,
    )
