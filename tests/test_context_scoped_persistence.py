from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.session_results import (
    load_last_result,
    load_result_history,
    save_last_result,
)
from core.study_resume import load_daily_run, save_daily_run
from db.models import Base, Competition, User, UserOPEC


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'context-scope.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _contexts(db):
    user = User(
        username="context-user",
        password_hash="x",
        role="user",
        subscription_tier="free",
    )
    dian = Competition(code="DIAN-2676-SCOPE", name="DIAN 2676")
    other = Competition(code="OTHER-SCOPE", name="Otro concurso")
    db.add_all([user, dian, other])
    db.flush()
    first = UserOPEC(
        user_id=user.id,
        competition_id=dian.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[],
        is_active=True,
    )
    same_competition = UserOPEC(
        user_id=user.id,
        competition_id=dian.id,
        opec_number="242699",
        job_title="Analista I",
        functions=[],
        is_active=False,
    )
    other_competition = UserOPEC(
        user_id=user.id,
        competition_id=other.id,
        opec_number="252097",
        job_title="Gestor de operaciones",
        functions=[],
        is_active=False,
    )
    db.add_all([first, same_competition, other_competition])
    db.commit()
    return user, first, same_competition, other_competition


def _activate(db, user, selected):
    db.query(UserOPEC).filter_by(user_id=user.id).update(
        {UserOPEC.is_active: False}, synchronize_session=False
    )
    selected.is_active = True
    db.commit()


def _run(question_id):
    return {
        "question_ids": [question_id],
        "answers": {},
        "checked_answers": {},
        "current_idx": 0,
        "total_time_limit": 600,
    }


def test_daily_run_isolated_when_opec_or_competition_changes(tmp_path):
    db = _session(tmp_path)
    try:
        user, first, same_competition, other_competition = _contexts(db)

        saved_first = save_daily_run(db, user.id, _run("question-first"))
        assert saved_first["competition_id"] == first.competition_id
        assert saved_first["opec_number"] == "236769"

        _activate(db, user, same_competition)
        assert load_daily_run(db, user.id) is None
        save_daily_run(db, user.id, _run("question-second"))
        assert load_daily_run(db, user.id)["question_ids"] == ["question-second"]

        _activate(db, user, other_competition)
        assert load_daily_run(db, user.id) is None
        save_daily_run(db, user.id, _run("question-other-contest"))

        _activate(db, user, first)
        restored_first = load_daily_run(db, user.id)
        assert restored_first["question_ids"] == ["question-first"]
        assert restored_first["competition_id"] == first.competition_id
        assert restored_first["opec_number"] == "236769"
    finally:
        db.close()


def test_last_result_and_history_are_isolated_by_active_context(tmp_path):
    db = _session(tmp_path)
    try:
        user, first, same_competition, other_competition = _contexts(db)

        save_last_result(db, user.id, {"score": 86, "session_kind": "simulation"})
        db.commit()
        assert load_last_result(db, user.id)["score"] == 86

        _activate(db, user, same_competition)
        assert load_last_result(db, user.id) is None
        assert load_result_history(db, user.id) == []
        save_last_result(db, user.id, {"score": 74, "session_kind": "daily"})
        db.commit()

        _activate(db, user, other_competition)
        assert load_last_result(db, user.id) is None
        assert load_result_history(db, user.id) == []
        save_last_result(db, user.id, {"score": 91, "session_kind": "simulation"})
        db.commit()

        _activate(db, user, first)
        first_result = load_last_result(db, user.id)
        first_history = load_result_history(db, user.id)
        assert first_result["score"] == 86
        assert first_result["competition_id"] == first.competition_id
        assert first_result["opec_number"] == "236769"
        assert [item["score"] for item in first_history] == [86]
    finally:
        db.close()


def test_explicit_context_keeps_legacy_callers_optional(tmp_path):
    db = _session(tmp_path)
    try:
        save_last_result(
            db,
            999,
            {"score": 88},
            competition_id=12,
            opec_number="236769",
        )
        save_daily_run(
            db,
            999,
            _run("explicit-question"),
            competition_id=12,
            opec_number="236769",
        )
        db.commit()

        assert load_last_result(db, 999) is None
        assert load_daily_run(db, 999) is None
        assert load_last_result(db, 999, 12, "236769")["score"] == 88
        assert load_daily_run(db, 999, 12, "236769")["question_ids"] == [
            "explicit-question"
        ]
    finally:
        db.close()
