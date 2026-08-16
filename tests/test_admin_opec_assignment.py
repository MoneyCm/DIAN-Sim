from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import admin_opec_assignment
from core.access_control import AdminPermissionDenied
from core.admin_opec_assignment import AssignableOPECNotFound, assign_prepared_opec
from db.models import Base, Competition, User


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_admin_can_assign_and_activate_a_prepared_opec(monkeypatch):
    db = _db()
    user = User(username="marisol", password_hash="x", role="user", subscription_tier="free")
    admin = User(username="admin", password_hash="x", role="admin", subscription_tier="free")
    competition = Competition(code="TEST", name="Concurso", is_active=True)
    db.add_all([user, admin, competition])
    db.commit()
    monkeypatch.setattr(admin_opec_assignment, "find_reusable_opec", lambda *_: {
        "opec_number": "242699", "job_title": "Analista I", "level": "Técnico",
        "purpose": "Apoyar", "functions": ["Función"], "requirements": "Título",
        "competition": {"id": competition.id},
    })

    assigned = assign_prepared_opec(
        db, user.id, "242699", actor_user_id=admin.id
    )
    db.commit()
    assert assigned.user_id == user.id
    assert assigned.opec_number == "242699"
    assert assigned.is_active is True


def test_admin_assignment_rejects_an_opec_that_is_not_prepared(monkeypatch):
    db = _db()
    user = User(username="marisol", password_hash="x", role="user", subscription_tier="free")
    admin = User(username="admin", password_hash="x", role="admin", subscription_tier="free")
    db.add_all([user, admin])
    db.commit()
    monkeypatch.setattr(admin_opec_assignment, "find_reusable_opec", lambda *_: None)

    try:
        assign_prepared_opec(
            db, user.id, "999999", actor_user_id=admin.id
        )
    except AssignableOPECNotFound:
        pass
    else:
        raise AssertionError("An unprepared OPEC must not be assigned")


def test_regular_user_cannot_invoke_admin_assignment_service(monkeypatch):
    db = _db()
    target = User(username="target", password_hash="x", role="user")
    actor = User(username="actor", password_hash="x", role="user")
    db.add_all([target, actor])
    db.commit()
    lookup_called = False

    def fake_lookup(*_args):
        nonlocal lookup_called
        lookup_called = True
        return None

    monkeypatch.setattr(admin_opec_assignment, "find_reusable_opec", fake_lookup)
    try:
        assign_prepared_opec(
            db, target.id, "242699", actor_user_id=actor.id
        )
    except AdminPermissionDenied:
        pass
    else:
        raise AssertionError("A regular user must not invoke an admin mutation")
    assert lookup_called is False
