"""Configuración y selección equilibrada para simulacros tipo examen."""

from dataclasses import dataclass
from collections import defaultdict, deque


UAPA_COMPETITION_CODE = "ALIMENTACION-ESCOLAR-ABIERTO"


@dataclass(frozen=True)
class RealExamBlueprint:
    title: str
    target_cases: int
    questions_per_case: int = 3
    minutes_per_question: int = 2

    @property
    def target_questions(self):
        return self.target_cases * self.questions_per_case

    @property
    def target_minutes(self):
        return self.target_questions * self.minutes_per_question


def blueprint_for_competition(code: str | None, *, is_pro: bool = False,
                              official_case_count: int | None = None):
    if code == UAPA_COMPETITION_CODE:
        return RealExamBlueprint("Simulacro UApA · Arquitectura y Gestión TI", 10)
    if official_case_count is not None:
        if official_case_count >= 20:
            return RealExamBlueprint("Simulacro Tipo Examen · 60 preguntas", 20)
        if official_case_count >= 10:
            return RealExamBlueprint("Simulacro Tipo Examen · 30 preguntas", 10)
        if official_case_count >= 3:
            return RealExamBlueprint("Simulacro Tipo Examen · Banco inicial", official_case_count)
    return RealExamBlueprint("Simulacro Tipo Examen", 3 if is_pro else 2)


def select_balanced_blocks(blocks, target_count: int, preferred_topics=()):
    """Distribuye bloques entre temas y prioriza debilidades sin romper tripletas."""
    if target_count <= 0:
        return []
    preferred = {topic: index for index, topic in enumerate(preferred_topics or [])}
    grouped = defaultdict(deque)
    for block in blocks:
        topic = getattr(block, "topic", None) or "General"
        grouped[topic].append(block)
    topics = sorted(grouped, key=lambda topic: (preferred.get(topic, len(preferred)), topic))
    selected = []
    while topics and len(selected) < target_count:
        next_topics = []
        for topic in topics:
            if len(selected) >= target_count:
                break
            queue = grouped[topic]
            if queue:
                selected.append(queue.popleft())
            if queue:
                next_topics.append(topic)
        topics = next_topics
    return selected
