import ast
from pathlib import Path
from types import SimpleNamespace

from core.question_opec_scope import question_matches_opec


PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "pages" / "Simulacro_Real.py"


def _page_source():
    return PAGE_PATH.read_text(encoding="utf-8-sig")


def _page_functions(*names):
    """Load selected pure helpers without executing the Streamlit page."""
    tree = ast.parse(_page_source(), filename=str(PAGE_PATH))
    selected = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    assert {node.name for node in selected} == set(names)
    namespace = {
        "question_matches_opec": question_matches_opec,
        "build_trusted_pjs_case_blocks": (
            lambda cases, **kwargs: [
                case for case in cases
                if all(
                    question.question_id in kwargs["eligible_question_ids"]
                    for question in case.questions
                )
            ]
        ),
    }
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(PAGE_PATH), "exec"), namespace)
    return [namespace[name] for name in names]


def _question(opec_number=None, question_id="q"):
    report = {"scope": {"opec_number": opec_number}} if opec_number else {}
    return SimpleNamespace(
        question_id=question_id,
        case_id=None,
        case_study=None,
        topic="Tema",
        micro_competencia="",
        competency="",
        source_refs="",
        stem="Pregunta",
        quality_report=report,
    )


def _block(*opec_numbers):
    return SimpleNamespace(questions=[_question(number) for number in opec_numbers])


def test_reviewed_block_filter_rejects_mixed_and_unscoped_questions():
    block_matches, filter_blocks = _page_functions(
        "_block_matches_opec", "_reviewed_blocks_for_opec"
    )
    valid = _block("236769", "236769", "236769")
    other = _block("242699", "242699", "242699")
    mixed = _block("236769", "242699", "236769")
    unscoped = _block("236769", None, "236769")

    assert block_matches(valid, "236769")
    assert not block_matches(other, "236769")
    assert not block_matches(mixed, "236769")
    assert not block_matches(unscoped, "236769")
    valid.questions[0].question_id = "valid-1"
    valid.questions[1].question_id = "valid-2"
    valid.questions[2].question_id = "valid-3"
    assert filter_blocks(
        [valid, other, mixed, unscoped],
        "236769",
        {"valid-1", "valid-2", "valid-3"},
    ) == [valid]


def test_exam_context_requires_same_competition_and_opec():
    (same_context,) = _page_functions("_same_exam_context")

    assert same_context(1, "236769", 1, "236769")
    assert not same_context(1, "236769", 1, "242699")
    assert not same_context(1, "236769", 2, "236769")
    assert not same_context(None, "236769", 1, "236769")
    assert not same_context("invalid", "236769", 1, "236769")


def test_inventory_loader_and_session_sanitizer_use_opec_scope():
    source = _page_source()

    assert source.count("_reviewed_blocks_for_opec(") >= 3
    assert "bank_partitions=(partition,)" in source
    assert 'partition="measurement"' in source
    assert "eligible_question_ids" in source
    assert "st.session_state.exam_competition_id = competition_id" in source
    assert "st.session_state.exam_opec_number = opec_number" in source
    assert "_same_exam_context(" in source
    assert "_reset_invalid_exam_state(clear_review=True)" in source
