from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.opec_lookup import attach_reusable_opec_to_user, find_reusable_opec, normalize_opec_number
from db.models import Base, Competition, User, UserOPEC


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_lookup_returns_public_job_fields_without_source_user_identity():
    db = _db()
    competition = Competition(code="NEW", name="Concurso nuevo", is_active=True)
    source_user = User(username="source", email="source@example.com", password_hash="x")
    db.add_all([competition, source_user])
    db.flush()
    db.add(UserOPEC(
        user_id=source_user.id, competition_id=competition.id, opec_number="123456",
        job_title="Profesional", level="Profesional", purpose="Gestionar proyectos",
        functions=["Formular planes", "Revisar indicadores"], requirements="Título profesional",
        is_active=True,
    ))
    db.commit()
    result = find_reusable_opec(db, "OPEC 123456")
    assert result["job_title"] == "Profesional"
    assert "user_id" not in result
    assert "email" not in result
    assert result["competition"]["code"] == "NEW"


def test_incomplete_profile_is_not_reused():
    db = _db()
    db.add(UserOPEC(
        opec_number="999999", job_title="Profesional", functions=[], is_active=False
    ))
    db.commit()
    assert find_reusable_opec(db, "999999") is None


def test_reusable_profile_can_be_attached_and_activated_for_another_user():
    db = _db()
    user = User(username="target", email="target@example.com", password_hash="x")
    competition = Competition(code="NEW", name="Nuevo", is_active=True)
    db.add_all([user, competition])
    db.flush()
    profile = {
        "opec_number": "123456", "job_title": "Profesional", "level": "Profesional",
        "purpose": "Gestionar", "functions": ["Planear"], "requirements": "Título",
        "competition": {"id": competition.id},
    }
    row = attach_reusable_opec_to_user(db, user.id, profile)
    db.commit()
    assert row.is_active is True
    assert row.user_id == user.id
    assert normalize_opec_number("OPEC # 123-456") == "123456"
