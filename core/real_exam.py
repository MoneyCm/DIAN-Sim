"""Configuración provisional y selección equilibrada para prácticas PJS.

La metodología de Prueba de Juicio Situacional está sustentada para DIAN 2676.
La cantidad de preguntas, la duración y los ejes definitivos del cuadernillo no
están publicados; por eso los valores de este módulo son parámetros editables
del simulador y no especificaciones oficiales del examen.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
import math


UAPA_COMPETITION_CODE = "ALIMENTACION-ESCOLAR-ABIERTO"
PJS_METHODOLOGY_STATUS = "officially_supported_for_dian_2676"
EXAM_PARAMETERS_STATUS = "provisional_editable_pending_goa"


@dataclass(frozen=True)
class RealExamBlueprint:
    title: str
    target_cases: int
    questions_per_case: int = 3
    minutes_per_question: float = 2.0
    target_question_count: int | None = None
    navigation_mode: str = "sequential"
    methodology_status: str = PJS_METHODOLOGY_STATUS
    parameter_status: str = EXAM_PARAMETERS_STATUS

    @property
    def target_questions(self):
        if self.target_question_count is not None:
            return self.target_question_count
        return self.target_cases * self.questions_per_case

    @property
    def target_minutes(self):
        return math.ceil(self.target_questions * self.minutes_per_question)

    @property
    def official_question_count(self):
        """The official booklet size is not published as of 2026-08-15."""
        return None

    @property
    def official_duration_minutes(self):
        """The official test duration is not published as of 2026-08-15."""
        return None


def blueprint_for_competition(
    code: str | None,
    *,
    is_pro: bool = False,
    reviewed_case_count: int | None = None,
    official_case_count: int | None = None,
    questions_per_case: int = 3,
    minutes_per_question: float = 2.0,
    target_question_count: int | None = None,
    navigation_mode: str = "sequential",
):
    """Build an editable practice plan from the reviewed local inventory.

    ``official_case_count`` remains as a compatibility alias for existing
    callers. Despite its historical name, it is a count of reviewed local
    cases and must not be presented as an official exam quantity.
    """
    inventory_case_count = (
        reviewed_case_count
        if reviewed_case_count is not None
        else official_case_count
    )

    def practice_blueprint(
        title: str,
        target_cases: int,
        *,
        exact_question_count: int | None = None,
    ):
        return RealExamBlueprint(
            title,
            target_cases,
            questions_per_case=max(1, int(questions_per_case)),
            minutes_per_question=max(0.1, float(minutes_per_question)),
            target_question_count=exact_question_count,
            navigation_mode=str(navigation_mode or "sequential"),
        )

    if target_question_count is not None:
        target_questions = max(1, int(target_question_count))
        target_cases = math.ceil(target_questions / max(1, int(questions_per_case)))
        return practice_blueprint(
            f"Práctica PJS cronometrada · {target_questions} preguntas "
            "(configuración interna provisional)",
            target_cases,
            exact_question_count=target_questions,
        )

    if code == UAPA_COMPETITION_CODE:
        return practice_blueprint("Simulacro UApA · Arquitectura y Gestión TI", 10)
    if inventory_case_count is not None:
        if inventory_case_count >= 20:
            return practice_blueprint(
                "Práctica PJS cronometrada · 60 preguntas (configuración provisional)",
                20,
            )
        if inventory_case_count >= 10:
            return practice_blueprint(
                "Práctica PJS cronometrada · 30 preguntas (configuración provisional)",
                10,
            )
        if inventory_case_count >= 3:
            return practice_blueprint(
                "Práctica PJS cronometrada · banco inicial (configuración provisional)",
                inventory_case_count,
            )
    return practice_blueprint(
        "Práctica PJS cronometrada (configuración provisional)",
        3 if is_pro else 2,
    )


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
