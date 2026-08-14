from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.user_opec_management import OPECNotFoundForUser, activate_opec
from db.models import Base, User, UserOPEC


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_activation_is_limited_to_the_users_own_opec_and_deactivates_the_rest():
    db = _db()
    user = User(username="ana", password_hash="x", role="user", subscription_tier="free")
    other = User(username="bea", password_hash="x", role="user", subscription_tier="free")
    db.add_all([user, other])
    db.flush()
    first = UserOPEC(user_id=user.id, opec_number="1", job_title="Uno", is_active=True)
    second = UserOPEC(user_id=user.id, opec_number="2", job_title="Dos", is_active=False)
    foreign = UserOPEC(user_id=other.id, opec_number="3", job_title="Tres", is_active=True)
    db.add_all([first, second, foreign])
    db.commit()

    activated = activate_opec(db, user.id, second.id)
    db.commit()
    assert activated.id == second.id
    assert db.get(UserOPEC, first.id).is_active is False
    assert db.get(UserOPEC, second.id).is_active is True
    assert db.get(UserOPEC, foreign.id).is_active is True

    try:
        activate_opec(db, user.id, foreign.id)
    except OPECNotFoundForUser:
        pass
    else:
        raise AssertionError("A user must not activate another user's OPEC")
