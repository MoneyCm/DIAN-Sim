from datetime import datetime
from typing import List, Optional, Union, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class QuestionBase(BaseModel):
    track: str
    competency: str
    topic: str
    difficulty: int = Field(ge=1, le=5)
    stem: str
    options_json: Dict[str, str]  # e.g., {"A": "Option 1", "B": "Option 2"}
    correct_key: Optional[str] = None
    rationale: Optional[str] = None
    source_refs: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    question_id: UUID
    created_at: datetime
    hash_norm: str

class AttemptBase(BaseModel):
    question_id: UUID
    chosen_key: str
    is_correct: bool
    time_sec: Optional[int] = None
    confidence_1_5: Optional[int] = None
    error_tag: Optional[str] = None
    notes: Optional[str] = None

class AttemptCreate(AttemptBase):
    pass

class Attempt(AttemptBase):
    attempt_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SkillBase(BaseModel):
    track: str
    competency: str
    topic: str
    mastery_score: float = Field(ge=0.0, le=100.0)
    priority_weight: float
    
    model_config = ConfigDict(from_attributes=True)

class Skill(SkillBase):
    skill_id: UUID
    last_seen: Optional[datetime] = None
    updated_at: datetime
