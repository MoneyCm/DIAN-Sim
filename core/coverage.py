from __future__ import annotations

from collections import defaultdict

from core.exam_format import has_source_grounded_review


MIN_QUESTIONS_PER_AREA = 5
MIN_ATTEMPTS_PER_TOPIC = 3


def build_coverage_rows(questions, performances) -> list[dict]:
    """Summarize bank quality and user evidence without inventing syllabus coverage."""
    performance_by_question = {
        item.question_id: item for item in performances
    }
    grouped = defaultdict(lambda: {
        "questions": 0,
        "trusted": 0,
        "topics": set(),
        "topic_attempts": defaultdict(int),
    })

    for question in questions:
        area = (
            getattr(question, "macro_dominio", None)
            or getattr(question, "track", None)
            or "Sin clasificar"
        )
        topic = getattr(question, "topic", None) or "Sin tema"
        bucket = grouped[area]
        bucket["questions"] += 1
        bucket["topics"].add(topic)
        if bool(getattr(question, "is_verified", False)) and has_source_grounded_review(question):
            bucket["trusted"] += 1
        performance = performance_by_question.get(question.question_id)
        if performance:
            bucket["topic_attempts"][topic] += int(performance.hits or 0) + int(performance.misses or 0)

    rows = []
    for area, bucket in grouped.items():
        evaluated_topics = sum(
            attempts >= MIN_ATTEMPTS_PER_TOPIC
            for attempts in bucket["topic_attempts"].values()
        )
        topic_count = len(bucket["topics"])
        if bucket["questions"] < MIN_QUESTIONS_PER_AREA:
            status = "Faltan preguntas"
        elif bucket["trusted"] == 0:
            status = "Revisar calidad"
        elif evaluated_topics == 0:
            status = "Pendiente de práctica"
        elif evaluated_topics < topic_count:
            status = "Cobertura parcial"
        else:
            status = "Con evidencia"
        rows.append({
            "area": area,
            "questions": bucket["questions"],
            "trusted": bucket["trusted"],
            "topics": topic_count,
            "evaluated_topics": evaluated_topics,
            "status": status,
        })
    return sorted(rows, key=lambda row: (row["status"] == "Con evidencia", row["area"]))

