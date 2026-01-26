import datetime
import json
import uuid
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, relationship, configure_mappers, backref

# --- SQLAlchemy 2.0 Base Clase ---
class Base(DeclarativeBase):
    pass

# 1. Definimos las clases que NO dependen de User (o que User necesita)
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

# 2. Definimos las clases secundarias (todas tienen FK a users.id)
class Attempt(Base):
    __tablename__ = "attempts"
    attempt_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.question_id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    chosen_key = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_sec = Column(Integer, nullable=True)
    confidence_1_5 = Column(Integer, nullable=True)
    error_tag = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    question = relationship("Question", backref="attempts")

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
    priority_weight = Column(Float, default=1.0)
    last_seen = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

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
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class QuestionPerformance(Base):
    __tablename__ = "question_performance"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    question_id = Column(String(36), ForeignKey("questions.question_id"))
    hits = Column(Integer, default=0)
    misses = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow)
    mastery_level = Column(Float, default=0.0)
    is_mastered = Column(Boolean, default=False)
    
    question = relationship("Question")

class Configuration(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True)
    key_name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 3. Definimos User al FINAL para que pueda referenciar a los anteriores por OBJETO
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Referencias directas a los objetos ya definidos
    opecs = relationship(UserOPEC, backref="user")
    performance = relationship(QuestionPerformance, backref="user")
    stats = relationship(UserStats, backref="user")
    attempts = relationship(Attempt, backref="user")
    achievements = relationship(Achievement, backref="user")
    skills = relationship(Skill, backref="user")

# Forzar configuración manual al final
configure_mappers()
