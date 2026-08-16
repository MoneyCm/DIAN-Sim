import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGE_PATHS = (
    PROJECT_ROOT / "app" / "pages" / "6_Dashboard.py",
    PROJECT_ROOT / "app" / "pages" / "12_Mapa_Estudio.py",
)


class _Policy:
    def __init__(self, *, target_score):
        self.target_score = target_score


class _PlanModel:
    pass


class _Query:
    def __init__(self, plan=None, error=None):
        self.plan = plan
        self.error = error
        self.filters = None

    def filter_by(self, **filters):
        self.filters = filters
        return self

    def first(self):
        if self.error:
            raise self.error
        return self.plan


class _Db:
    def __init__(self, plan=None, query_error=None):
        self.query_result = _Query(plan=plan, error=query_error)
        self.rollback_count = 0

    def query(self, model):
        assert model is _PlanModel
        return self.query_result

    def rollback(self):
        self.rollback_count += 1


def _load_helper(path: Path, evaluator):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_load_readiness_state"
    )
    isolated = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        "OpecStudyPlan": _PlanModel,
        "ReadinessPolicy": _Policy,
        "evaluate_opec_readiness": evaluator,
    }
    exec(compile(isolated, str(path), "exec"), namespace)
    return namespace["_load_readiness_state"]


@pytest.mark.parametrize("page_path", PAGE_PATHS)
def test_page_loader_uses_opec_plan_target_and_active_canonical_scope(page_path):
    assessment = object()
    captured = {}

    def evaluator(db, **kwargs):
        captured.update(kwargs)
        return assessment

    helper = _load_helper(page_path, evaluator)
    db = _Db(plan=SimpleNamespace(target_score=91.5))
    active_opec = SimpleNamespace(id=44, competition_id=2676)

    target, loaded, note = helper(
        db, user_id=7, active_opec=active_opec
    )

    assert target == 91.5
    assert loaded is assessment
    assert note is None
    assert db.query_result.filters == {
        "user_id": 7,
        "competition_id": 2676,
        "user_opec_id": 44,
    }
    assert captured["user_id"] == 7
    assert captured["user_opec_id"] == 44
    assert captured["policy"].target_score == 91.5


@pytest.mark.parametrize("page_path", PAGE_PATHS)
def test_page_loader_keeps_gates_pending_when_phase2_tables_are_unavailable(page_path):
    def unavailable_evaluator(*args, **kwargs):
        raise RuntimeError("missing measurement table")

    helper = _load_helper(page_path, unavailable_evaluator)
    db = _Db(query_error=RuntimeError("missing plan table"))
    active_opec = SimpleNamespace(id=44, competition_id=2676)

    target, assessment, note = helper(
        db, user_id=7, active_opec=active_opec
    )

    assert target == 85.0
    assert assessment is None
    assert "objetivo interno predeterminado de 85%" in note
    assert "puertas permanecen pendientes" in note
    assert "missing" not in note
    assert db.rollback_count == 2


@pytest.mark.parametrize("page_path", PAGE_PATHS)
def test_page_loader_falls_back_to_85_when_no_opec_plan_exists(page_path):
    assessment = object()
    captured = {}

    def evaluator(db, **kwargs):
        captured.update(kwargs)
        return assessment

    helper = _load_helper(page_path, evaluator)
    db = _Db(plan=None)
    active_opec = SimpleNamespace(id=44, competition_id=2676)

    target, loaded, note = helper(
        db, user_id=7, active_opec=active_opec
    )

    assert target == 85.0
    assert loaded is assessment
    assert note is None
    assert captured["policy"].target_score == 85.0


@pytest.mark.parametrize("page_path", PAGE_PATHS)
def test_readiness_pages_use_safe_separate_claims(page_path):
    source = page_path.read_text(encoding="utf-8")

    assert "evaluate_opec_readiness" in source
    assert "OpecStudyPlan" in source
    assert "Objetivo interno de precisión" in source
    assert "Mínimo oficial funcional" in source
    assert "OFFICIAL_FUNCTIONAL_MINIMUM_SCORE" in source
    assert "meta interna repetida " in source
    assert "no calcula aprobación" in source or "no es una predicción de aprobación" in source
    assert "garantiza ganar" not in source.casefold()
    assert "aprobaste el concurso" not in source.casefold()


def test_dashboard_distinguishes_reinforcement_from_the_85_readiness_target():
    source = PAGE_PATHS[0].read_text(encoding="utf-8")

    assert "Meta interna 70%" not in source
    assert "Umbral interno de refuerzo: 70%" in source
    assert "Repaso consolidado" in source
    assert "Maestría Real" not in source
    assert "evidencia mínima inicial" in source


def test_study_map_exposes_named_transparent_gates_and_internal_estimate():
    source = PAGE_PATHS[1].read_text(encoding="utf-8")

    assert "Puertas transparentes de la medición" in source
    assert "Fuentes y banco confiables" in source
    assert "Cobertura conjunta de nueve funciones" in source
    assert "Estimación interna de desempeño" in source
    assert "Dominio demostrado" not in source
