from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.learning.engine import (
    calculate_mastery,
    calculate_topic_priority,
    difficulty_for_mastery,
    schedule_next_review,
    select_next_question,
    topic_id_for,
)


NOW = datetime(2026, 8, 6, 12, 0)


def test_mastery_supports_correct_partial_and_incorrect():
    assert calculate_mastery(50, "correct", "medium") == 60
    assert calculate_mastery(50, "partial", "medium") == 52
    assert calculate_mastery(50, "incorrect", "medium") == 40


def test_mastery_rejects_unknown_values():
    with pytest.raises(ValueError):
        calculate_mastery(50, "almost", "medium")


def test_incorrect_high_confidence_is_reviewed_soon():
    incorrect = schedule_next_review("incorrect", "high", 30, now=NOW)
    correct = schedule_next_review("correct", "high", 80, now=NOW)
    assert incorrect < NOW + timedelta(days=2)
    assert correct > NOW + timedelta(days=7)


def test_priority_formula_favors_weak_overdue_error_prone_topic():
    weak = calculate_topic_priority(
        mastery_score=20,
        next_review_at=NOW - timedelta(days=1),
        recent_error_rate=0.8,
        low_confidence_rate=0.7,
        importance=2,
        last_studied_at=NOW - timedelta(days=40),
        now=NOW,
    )
    strong = calculate_topic_priority(
        mastery_score=90,
        next_review_at=NOW + timedelta(days=5),
        recent_error_rate=0.1,
        low_confidence_rate=0.1,
        importance=1,
        last_studied_at=NOW - timedelta(days=2),
        now=NOW,
    )
    assert weak > strong


def test_select_next_question_uses_priority_and_exclusions():
    questions = [
        SimpleNamespace(question_id="q1", track="F", competency="C", topic="Débil", difficulty=2),
        SimpleNamespace(question_id="q2", track="F", competency="C", topic="Fuerte", difficulty=2),
    ]
    priorities = {
        topic_id_for("F", "C", "Débil"): 0.9,
        topic_id_for("F", "C", "Fuerte"): 0.2,
    }
    assert select_next_question(questions, priorities).question_id == "q1"
    assert select_next_question(questions, priorities, excluded_question_ids={"q1"}).question_id == "q2"


def test_difficulty_unlocks_only_after_enough_evidence_and_mastery():
    assert difficulty_for_mastery(90, attempts=0) == 1
    assert difficulty_for_mastery(39, attempts=8) == 1
    assert difficulty_for_mastery(40, attempts=3) == 2
    assert difficulty_for_mastery(74, attempts=20) == 2
    assert difficulty_for_mastery(75, attempts=5) == 3


def test_adaptive_selector_prefers_difficulty_matching_topic_mastery():
    topic_id = topic_id_for("F", "C", "Arquitectura")
    questions = [
        SimpleNamespace(question_id="basic", track="F", competency="C", topic="Arquitectura", difficulty=1),
        SimpleNamespace(question_id="advanced", track="F", competency="C", topic="Arquitectura", difficulty=3),
    ]
    priorities = {topic_id: 0.8}
    assert select_next_question(
        questions, priorities, topic_mastery_scores={topic_id: 10}, topic_attempt_counts={topic_id: 2}
    ).question_id == "basic"
    assert select_next_question(
        questions, priorities, topic_mastery_scores={topic_id: 85}, topic_attempt_counts={topic_id: 8}
    ).question_id == "advanced"
