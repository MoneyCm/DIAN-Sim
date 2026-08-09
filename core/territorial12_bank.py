"""Read the reviewed 100-question Territorial 12 bank without importing Streamlit."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION_PAGE = PROJECT_ROOT / "app" / "pages" / "7_Configuracion_OPEC.py"


def load_reviewed_questions() -> list[tuple[str, dict, str, str, str]]:
    """Return the versioned 100-question bank stored alongside the OPEC UI.

    The OPEC configuration page owns the author-facing questions. Parsing its
    data declarations keeps one source of truth while avoiding execution of the
    Streamlit page during deployment maintenance.
    """
    source = CONFIGURATION_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CONFIGURATION_PAGE))
    assignments = {
        "TERRITORIAL_12_SEED",
        "TERRITORIAL_12_SECOND_SEED",
        "TERRITORIAL_12_SCENARIOS",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in assignments
            for target in node.targets
        ):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "build_territorial_12_scenario_questions":
            selected.append(node)

    namespace: dict = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(CONFIGURATION_PAGE), "exec"), namespace)
    questions = [
        (stem, options, correct, rationale, "Ficha OPEC 241130 y Acuerdo 36")
        for stem, options, correct, rationale in namespace["TERRITORIAL_12_SEED"]
    ]
    questions.extend(namespace["TERRITORIAL_12_SECOND_SEED"])
    questions.extend(namespace["build_territorial_12_scenario_questions"]())
    if len(questions) != 100 or len({question[0] for question in questions}) != 100:
        raise RuntimeError("El banco revisado de OPEC 241130 debe contener 100 preguntas únicas.")
    return questions
