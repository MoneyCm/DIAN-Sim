import ast
import datetime
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from db.models import Base, Competition, ErrorEpisode, User, UserOPEC


PAGE_PATH = Path(__file__).parents[1] / "app" / "pages" / "10_Repaso_Especial.py"


def _page_source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8-sig")


def _load_page_function(name: str, **dependencies):
    tree = ast.parse(_page_source())
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )
    namespace = dict(dependencies)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(PAGE_PATH), "exec"), namespace)
    return namespace[name]


def _database() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _episode(*, suffix, user, competition, user_opec, opec_number=None):
    return ErrorEpisode(
        learning_event_id=f"event-{suffix}",
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=user_opec.id,
        opec_number=opec_number or user_opec.opec_number,
        question_id=f"question-{suffix}",
        question_revision_id=f"revision-{suffix}",
        category="interpretation",
        status="scheduled",
    )


def test_canonical_query_is_strictly_scoped_to_user_competition_and_active_opec():
    db = _database()
    first_user = User(username="first", password_hash="hash")
    second_user = User(username="second", password_hash="hash")
    first_competition = Competition(code="DIAN", name="DIAN")
    second_competition = Competition(code="ADRES", name="ADRES")
    db.add_all([first_user, second_user, first_competition, second_competition])
    db.flush()

    active = UserOPEC(
        user_id=first_user.id,
        competition_id=first_competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[],
        is_active=True,
        updated_at=datetime.datetime(2026, 8, 15, 12, 0),
    )
    older_active = UserOPEC(
        user_id=first_user.id,
        competition_id=first_competition.id,
        opec_number="241130",
        job_title="Profesional",
        functions=[],
        is_active=True,
        updated_at=datetime.datetime(2026, 8, 14, 12, 0),
    )
    other_competition = UserOPEC(
        user_id=first_user.id,
        competition_id=second_competition.id,
        opec_number="252097",
        job_title="Gestor de operaciones",
        functions=[],
        is_active=True,
    )
    other_user = UserOPEC(
        user_id=second_user.id,
        competition_id=first_competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[],
        is_active=True,
    )
    db.add_all([active, older_active, other_competition, other_user])
    db.flush()
    db.add_all(
        [
            _episode(
                suffix="selected",
                user=first_user,
                competition=first_competition,
                user_opec=active,
            ),
            _episode(
                suffix="older-active",
                user=first_user,
                competition=first_competition,
                user_opec=older_active,
            ),
            _episode(
                suffix="competition",
                user=first_user,
                competition=second_competition,
                user_opec=other_competition,
            ),
            _episode(
                suffix="user",
                user=second_user,
                competition=first_competition,
                user_opec=other_user,
            ),
            _episode(
                suffix="mismatched-number",
                user=first_user,
                competition=first_competition,
                user_opec=active,
                opec_number="999999",
            ),
        ]
    )
    db.commit()

    resolve_active = _load_page_function("_active_user_opec", UserOPEC=UserOPEC)
    build_query = _load_page_function("_canonical_error_query", ErrorEpisode=ErrorEpisode)
    resolved = resolve_active(
        db,
        user_id=first_user.id,
        competition_id=first_competition.id,
    )
    rows = build_query(
        db,
        user_id=first_user.id,
        competition_id=first_competition.id,
        user_opec=resolved,
    ).all()

    assert resolved.id == active.id
    assert [row.learning_event_id for row in rows] == ["event-selected"]


def test_schema_probe_requires_every_phase2_error_notebook_table():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table_names = (
        "error_episodes",
        "opec_learning_events",
        "opec_learning_sessions",
        "question_revisions",
    )
    probe = _load_page_function(
        "_canonical_error_notebook_available",
        inspect=inspect,
        PHASE2_ERROR_NOTEBOOK_TABLES=table_names,
    )
    with engine.begin() as connection:
        for table_name in table_names[:-1]:
            connection.exec_driver_sql(f"CREATE TABLE {table_name} (id INTEGER)")
    with Session(engine) as db:
        assert probe(db) is False

    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE question_revisions (id INTEGER)")
    with Session(engine) as db:
        assert probe(db) is True


def test_source_reference_formatter_handles_canonical_verification_payload():
    formatter = _load_page_function("_source_reference_text", Mapping=Mapping)
    rendered = formatter(
        {
            "declared": "Estatuto Tributario",
            "verification": {
                "locator": "Artículo 616-1",
                "official_url": "https://www.dian.gov.co/normativa",
            },
        }
    )
    assert "Estatuto Tributario" in rendered
    assert "Artículo 616-1" in rendered
    assert "https://www.dian.gov.co/normativa" in rendered


def test_page_exposes_all_canonical_fields_and_no_manual_overcome_control():
    source = _page_source()
    required_labels = (
        "**Categoría:**",
        "**Razón del error:**",
        "**Regla para recordar:**",
        "**Fuente:**",
        "**Microlección:**",
        "**Próximo repaso:**",
        "**Estado:**",
    )
    assert all(label in source for label in required_labels)
    assert "refresh_error_episode(session, episode, now=now)" in source
    assert "_render_legacy_error_bank(" in source

    tree = ast.parse(source)
    canonical_renderer = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_render_canonical_error_notebook"
    )
    calls = [node for node in ast.walk(canonical_renderer) if isinstance(node, ast.Call)]
    assert not any(
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "st"
        and call.func.attr == "button"
        for call in calls
    )
    assignments = [node for node in ast.walk(canonical_renderer) if isinstance(node, ast.Assign)]
    assert not any(
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "episode"
        and target.attr in {"status", "overcome_at", "transfer_event_id"}
        for assignment in assignments
        for target in assignment.targets
    )
