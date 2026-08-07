"""Carga de forma idempotente el banco local de Territorial 12.

Ejecutar desde la raíz del proyecto:
    .venv/Scripts/python.exe scripts/data/seed_territorial12_local.py
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_PAGE = PROJECT_ROOT / "app" / "pages" / "7_Configuracion_OPEC.py"
LOCAL_DB = PROJECT_ROOT / "dian_sim.db"

sys.path.insert(0, str(PROJECT_ROOT))
os.environ["DATABASE_URL"] = f"sqlite:///{LOCAL_DB.as_posix()}"
os.environ["DIAN_SIM_ENV"] = "development"
os.environ["REQUIRE_DATABASE_URL"] = "false"


def load_question_bank() -> list[tuple[str, dict, str, str, str]]:
    """Extrae el banco de la página sin ejecutar la interfaz de Streamlit."""
    source = APP_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(APP_PAGE))
    required_assignments = {
        "TERRITORIAL_12_SEED",
        "TERRITORIAL_12_SECOND_SEED",
        "TERRITORIAL_12_SCENARIOS",
    }
    selected_nodes: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in required_assignments
            for target in node.targets
        ):
            selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "build_territorial_12_scenario_questions":
            selected_nodes.append(node)

    namespace: dict = {}
    module = ast.Module(body=selected_nodes, type_ignores=[])
    exec(compile(module, str(APP_PAGE), "exec"), namespace)

    rows = [
        (stem, options, correct, rationale, "Ficha OPEC 241130 y Acuerdo 36")
        for stem, options, correct, rationale in namespace["TERRITORIAL_12_SEED"]
    ]
    rows.extend(namespace["TERRITORIAL_12_SECOND_SEED"])
    rows.extend(namespace["build_territorial_12_scenario_questions"]())
    return rows


def main() -> None:
    from db.models import Competition, Question
    from db.session import SessionLocal

    rows = load_question_bank()
    if len(rows) != 100:
        raise RuntimeError(f"El banco debe contener exactamente 100 preguntas; contiene {len(rows)}.")
    if len({row[0] for row in rows}) != len(rows):
        raise RuntimeError("El banco contiene enunciados duplicados.")

    db = SessionLocal()
    try:
        competition = db.query(Competition).filter_by(code="TERRITORIAL-12-BOLIVAR-2685").first()
        if competition is None:
            competition = Competition(
                code="TERRITORIAL-12-BOLIVAR-2685",
                name="Territorial 12 - Gobernación de Bolívar",
                entity="Gobernación de Bolívar",
                description="Proceso de Selección Territorial 12, OPEC 241130.",
                is_active=True,
            )
            db.add(competition)
            db.flush()

        existing_stems = {
            stem
            for (stem,) in db.query(Question.stem)
            .filter(Question.competition_id == competition.id)
            .all()
        }
        created = 0
        for stem, options, correct, rationale, source_ref in rows:
            if stem in existing_stems:
                continue
            digest = hashlib.sha256(
                f"TERRITORIAL-12-BOLIVAR-2685|{stem}".encode("utf-8")
            ).hexdigest()
            db.add(
                Question(
                    competition_id=competition.id,
                    track="FUNCIONAL",
                    competency="Planeación y gestión pública",
                    topic="Territorial 12 - Bolívar",
                    macro_dominio="Planeación territorial",
                    micro_competencia="Planeación, seguimiento y evaluación",
                    difficulty=2,
                    question_type="SITUATIONAL",
                    stem=stem,
                    options_json=options,
                    correct_key=correct,
                    rationale=rationale,
                    source_refs=source_ref,
                    hash_norm=digest,
                    is_verified=True,
                )
            )
            created += 1

        db.commit()
        total = (
            db.query(Question)
            .filter(Question.competition_id == competition.id)
            .count()
        )
        bank_total = (
            db.query(Question)
            .filter(
                Question.competition_id == competition.id,
                Question.stem.in_([row[0] for row in rows]),
            )
            .count()
        )
        print(f"Preguntas agregadas: {created}")
        print(f"Preguntas del banco verificadas: {bank_total}/100")
        print(f"Total de preguntas del concurso en SQLite local: {total}")
        if bank_total != 100:
            raise RuntimeError("No se pudieron verificar las 100 preguntas en la base local.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
