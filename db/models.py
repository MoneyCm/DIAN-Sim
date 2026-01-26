from __future__ import annotations
import datetime
import uuid
import sys
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, registry

# --- EL EXORCISMO TOTAL v19.0 - MIKEY ---
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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    opecs: Mapped[List["UserOPEC"]] = relationship("UserOPEC", back_populates="user", cascade="all, delete-orphan")
    performance: Mapped[List["QuestionPerformance"]] = relationship("QuestionPerformance", back_populates="user", cascade="all, delete-orphan")
    stats: Mapped[Optional["UserStats"]] = relationship("UserStats", back_populates="user", cascade="all, delete-orphan")
    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["Achievement"]] = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[List["Skill"]] = relationship("Skill", back_populates="user", cascade="all, delete-orphan")

class UserOPEC(Base):
    __tablename__ = "user_opec"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    opec_number: Mapped[str] = mapped_column(String)
    job_title: Mapped[str] = mapped_column(String)
    level: Mapped[Optional[str]] = mapped_column(String)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    functions: Mapped[Optional[dict]] = mapped_column(JSON)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="opecs")

class Question(Base):
    __tablename__ = "questions"
    question_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track: Mapped[str] = mapped_column(String)
    competency: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    macro_dominio: Mapped[Optional[str]] = mapped_column(String)
    micro_competencia: Mapped[Optional[str]] = mapped_column(String)
    difficulty: Mapped[int] = mapped_column(Integer)
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[dict] = mapped_column(JSON)
    correct_key: Mapped[Optional[str]] = mapped_column(String)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    source_refs: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    hash_norm: Mapped[str] = mapped_column(String, unique=True)

    attempts: Mapped[List["Attempt"]] = relationship("Attempt", back_populates="question")
    perf_entries: Mapped[List["QuestionPerformance"]] = relationship("QuestionPerformance", back_populates="question")

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
    last_attempt: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="performance")
    question: Mapped["Question"] = relationship("Question", back_populates="perf_entries")

class Configuration(Base):
    __tablename__ = "configurations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_name: Mapped[str] = mapped_column(String, unique=True)
    value: Mapped[str] = mapped_column(String)

print("✅ [DB_MODELS] Modelos exorcizados y registrados en v19. Mikey.", file=sys.stderr)
# Forzamos configuración inmediata para detectar errores de resolución de nombres
from sqlalchemy.orm import configure_mappers
try:
    configure_mappers()
    print("✨ [DB_MODELS] Mappers configurados exitosamente. Mikey.", file=sys.stderr)
except Exception as e:
    print(f"🔥 [DB_MODELS] Error en configuración de mappers: {e}", file=sys.stderr)
