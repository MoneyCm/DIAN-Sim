from typing import Optional

from sqlalchemy.orm import Session

from db.models import Competition, UserOPEC


DEFAULT_COMPETITION_CODE = "DIAN-2676"

BUILTIN_COMPETITIONS = (
    {
        "code": "ALIMENTACION-ESCOLAR-ABIERTO",
        "name": "Alimentación Escolar - Alimentos para Aprender - Abierto",
        "entity": "Unidad Administrativa Especial de Alimentación Escolar - Alimentos para Aprender",
        "description": "Proceso de selección modalidad Abierto de la UApA.",
    },
)


def ensure_builtin_competitions(db: Session) -> None:
    """Registra los concursos soportados por la interfaz de forma idempotente."""
    changed = False
    for values in BUILTIN_COMPETITIONS:
        competition = db.query(Competition).filter_by(code=values["code"]).first()
        if competition is None:
            db.add(Competition(**values, is_active=True))
            changed = True
        elif not competition.is_active:
            competition.is_active = True
            changed = True
    if changed:
        db.commit()


def get_default_competition(db: Session) -> Optional[Competition]:
    return db.query(Competition).filter_by(code=DEFAULT_COMPETITION_CODE).first()


def get_active_opec(db: Session, user_id: int) -> Optional[UserOPEC]:
    return db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()


def get_active_competition(db: Session, user_id: int) -> Optional[Competition]:
    active_opec = get_active_opec(db, user_id)
    if active_opec and active_opec.competition_id:
        competition = db.get(Competition, active_opec.competition_id)
        if competition:
            return competition
    return get_default_competition(db)


def get_active_competition_id(db: Session, user_id: int) -> Optional[int]:
    competition = get_active_competition(db, user_id)
    return competition.id if competition else None


def activate_competition(db: Session, user_id: int, competition_id: int) -> None:
    """Activa el cargo más reciente del concurso y desactiva los demás."""
    db.query(UserOPEC).filter_by(user_id=user_id).update({UserOPEC.is_active: False})
    target = (
        db.query(UserOPEC)
        .filter_by(user_id=user_id, competition_id=competition_id)
        .order_by(UserOPEC.updated_at.desc())
        .first()
    )
    if target:
        target.is_active = True
