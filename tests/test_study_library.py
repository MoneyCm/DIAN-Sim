import pytest

from core.study_library import (
    PROGRESS_LABELS,
    build_study_library,
    load_library_progress,
    precise_locator,
    save_library_status,
)
from db.models import Base, Competition, User, UserOPEC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _scope(db, username="user", opec="236769"):
    user = User(username=username, password_hash="x", role="user")
    competition = Competition(
        code=f"DIAN-2676-{username}", name="DIAN 2676", is_active=True
    )
    db.add_all([user, competition])
    db.flush()
    profile = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number=opec,
        job_title="Gestor III",
        is_active=True,
    )
    db.add(profile)
    db.commit()
    return user, competition, profile


def test_library_contains_only_demonstrably_linked_or_core_sources():
    documents = build_study_library("236769")
    assert documents
    assert all(document.function_numbers or "Base oficial" in document.relationship for document in documents)
    assert all(document.url.startswith("https://") for document in documents)
    assert any("no es temario oficial" in document.relationship for document in documents)


def test_library_never_invents_a_precise_locator_or_pedagogical_rule():
    documents = build_study_library("236769")
    tax_statute = next(item for item in documents if item.source_id == "tax_statute")
    assert tax_statute.locator_precise is False
    assert tax_statute.main_rule is None
    assert tax_statute.exception is None
    assert tax_statute.work_example is None
    assert precise_locator("Artículo 17; páginas 20-22") is True


def test_direct_question_links_are_counted_without_inferring_from_a_topic():
    documents = build_study_library(
        "236769",
        question_source_refs=(
            "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm · art. 746",
            "Tema tributario sin URL",
        ),
    )
    tax_statute = next(item for item in documents if item.source_id == "tax_statute")
    assert tax_statute.associated_question_count == 1


def test_progress_is_strictly_isolated_by_user_and_opec(db):
    user, competition, profile = _scope(db)
    other, _, other_profile = _scope(db, username="other", opec="999")
    save_library_status(
        db,
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=profile.id,
        opec_number=profile.opec_number,
        source_id="profile_at_fl_3006",
        status="studying",
    )
    assert load_library_progress(
        db,
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=profile.id,
        opec_number=profile.opec_number,
    ) == {"profile_at_fl_3006": "studying"}
    assert load_library_progress(
        db,
        user_id=other.id,
        competition_id=other_profile.competition_id,
        user_opec_id=other_profile.id,
        opec_number=other_profile.opec_number,
    ) == {}


def test_status_and_scope_are_validated(db):
    user, competition, profile = _scope(db)
    with pytest.raises(ValueError):
        save_library_status(
            db,
            user_id=user.id,
            competition_id=competition.id,
            user_opec_id=profile.id,
            opec_number=profile.opec_number,
            source_id="source",
            status="opened_app",
        )
    with pytest.raises(ValueError):
        save_library_status(
            db,
            user_id=user.id,
            competition_id=competition.id,
            user_opec_id=profile.id,
            opec_number=profile.opec_number,
            source_id="source",
            status="mastered",
        )
    with pytest.raises(ValueError):
        load_library_progress(
            db,
            user_id=user.id + 999,
            competition_id=competition.id,
            user_opec_id=profile.id,
            opec_number=profile.opec_number,
        )
    assert "mastered" in PROGRESS_LABELS


def test_unknown_opec_does_not_receive_an_invented_library():
    assert build_study_library("999999") == ()
