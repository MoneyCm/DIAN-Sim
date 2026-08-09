import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import competition_catalog
from db.models import Base, Competition


def test_catalog_sync_persists_profile_for_new_users(tmp_path, monkeypatch):
    profile_dir = tmp_path / "sample"
    profile_dir.mkdir()
    (profile_dir / "perfil_concurso.json").write_text(
        json.dumps(
            {
                "competition": {
                    "code": "PRUEBA-ABIERTO",
                    "name": "Concurso de prueba",
                    "entity": "Entidad de prueba",
                },
                "position": {"opec_number": "123456"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(competition_catalog, "CATALOG_ROOT", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    assert competition_catalog.sync_catalog_competitions(db) is True
    db.close()

    verified = Session()
    competition = verified.query(Competition).filter_by(code="PRUEBA-ABIERTO").one()
    assert competition.name == "Concurso de prueba"
    assert competition.entity == "Entidad de prueba"
    assert competition_catalog.sync_catalog_competitions(verified) is False
    verified.close()
