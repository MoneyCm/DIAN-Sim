import datetime
import uuid
import sys
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, configure_mappers

# Registro de carga para los logs de Streamlit
print("� [DB_MODELS] Iniciando Carga Ultra-Robusta v7.0 Mikey", file=sys.stderr)

Base = declarative_base()

# --- MODELOS --- (Definidos primero, sin relaciones complejas internas)

class Question(Base):
    __tablename__ = "questions"
    question_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track = Column(String, nullable=False)
    competency = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    macro_dominio = Column(String, nullable=True) 
    micro_competencia = Column(String, nullable=True) 
    difficulty = Column(Integer, nullable=False)
    stem = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=False)
    correct_key = Column(String, nullable=True)
    rationale = Column(Text, nullable=True)
    source_refs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    hash_norm = Column(String, unique=True, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserOPEC(Base):
    __tablename__ = "user_opec"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    opec_number = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    level = Column(String)
    purpose = Column(Text)
    functions = Column(JSON)
    requirements = Column(Text)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class Attempt(Base):
    __tablename__ = "attempts"
    attempt_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.question_id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    chosen_key = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_sec = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserStats(Base):
    __tablename__ = "user_stats"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.datetime.utcnow)

class Achievement(Base):
    __tablename__ = "achievements"
    achievement_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(String)
    icon = Column(String)
    unlocked_at = Column(DateTime, default=datetime.datetime.utcnow)

class Skill(Base):
    __tablename__ = "skills"
    skill_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    track = Column(String, nullable=False)
    competency = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    macro_dominio = Column(String, nullable=True)
    micro_competencia = Column(String, nullable=True)
    mastery_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class QuestionPerformance(Base):
    __tablename__ = "question_performance"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    question_id = Column(String(36), ForeignKey("questions.question_id"))
    hits = Column(Integer, default=0)
    misses = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow)

class Configuration(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True)
    key_name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)

# --- RELACIONES TARDÍAS ---
# Usamos backref para simplificar al máximo y evitar KeyError
User.opecs = relationship("UserOPEC", backref="user")
User.stats = relationship("UserStats", backref="user")
User.attempts = relationship("Attempt", backref="user")
User.achievements = relationship("Achievement", backref="user")
User.skills = relationship("Skill", backref="user")
User.performance = relationship("QuestionPerformance", backref="user")

Attempt.question = relationship("Question", backref="attempts")
QuestionPerformance.question = relationship("Question", backref="performance")

# Intentamos configurar mappers, si falla, al menos dejamos cargar el archivo
try:
    configure_mappers()
    print("✅ [DB_MODELS] Mappers listos.", file=sys.stderr)
except Exception as e:
    print(f"❌ [DB_MODELS] Fallo en mappers: {e}", file=sys.stderr)
