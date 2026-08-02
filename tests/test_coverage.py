from types import SimpleNamespace

from core.coverage import build_coverage_rows


def question(qid, area="Tributario", topic="Tema", trusted=True):
    return SimpleNamespace(
        question_id=qid,
        macro_dominio=area,
        track="FUNCIONAL",
        topic=topic,
        is_verified=trusted,
        quality_report={"review": "human_source_grounded"} if trusted else None,
    )


def performance(qid, hits=0, misses=0):
    return SimpleNamespace(question_id=qid, hits=hits, misses=misses)


def test_coverage_requires_bank_depth_before_calling_area_covered():
    rows = build_coverage_rows([question("1"), question("2")], [])
    assert rows[0]["status"] == "Faltan preguntas"


def test_coverage_separates_bank_quality_from_user_evidence():
    questions = [question(str(index)) for index in range(5)]
    pending = build_coverage_rows(questions, [performance("1", hits=2)])[0]
    evaluated = build_coverage_rows(questions, [performance("1", hits=3)])[0]
    assert pending["status"] == "Pendiente de práctica"
    assert evaluated["status"] == "Con evidencia"

