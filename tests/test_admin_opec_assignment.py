from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import admin_opec_assignment
from core.admin_opec_assignment import AssignableOPECNotFound, assign_prepared_opec
from db.models import Base, Competition, User


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_admin_can_assign_and_activate_a_prepared_opec(monkeypatch):
    db = _db()
    user = User(username="marisol", password_hash="x", role="user", subscription_tier="free")
    competition = Competition(code="TEST", name="Concurso", is_active=True)
    db.add_all([user, competition])
    db.commit()
    monkeypatch.setattr(admin_opec_assignment, "find_reusable_opec", lambda *_: {
        "opec_number": "242699", "job_title": "Analista I", "level": "Técnico",
        "purpose": "Apoyar", "functions": ["Función"], "requirements": "Título",
        "competition": {"id": competition.id},
    })

    assigned = assign_prepared_opec(db, user.id, "242699")
    db.commit()
    assert assigned.user_id == user.id
    assert assigned.opec_number == "242699"
    assert assigned.is_active is True


def test_admin_assignment_rejects_an_opec_that_is_not_prepared(monkeypatch):
    db = _db()
    user = User(username="marisol", password_hash="x", role="user", subscription_tier="free")
    db.add(user)
    db.commit()
    monkeypatch.setattr(admin_opec_assignment, "find_reusable_opec", lambda *_: None)

    try:
        assign_prepared_opec(db, user.id, "999999")
    except AssignableOPECNotFound:
        pass
    else:
        raise AssertionError("An unprepared OPEC must not be assigned")
