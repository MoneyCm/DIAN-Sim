from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import core.normativa as normativa_module
from core.normativa import MAX_EMBEDDINGS_PER_RUN, NormativaManager
from db.models import Base, NormativaChunk


def _factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_pdf_indexing_is_lexical_and_never_spends_embedding_budget(
    tmp_path, monkeypatch
):
    factory = _factory()
    monkeypatch.setattr(normativa_module, "SessionLocal", factory)
    monkeypatch.setattr(
        normativa_module,
        "extract_pdf_pages",
        lambda _payload: ["regla tributaria oficial " * 10],
    )
    (tmp_path / "norma.pdf").write_bytes(b"validated upstream")
    manager = NormativaManager(str(tmp_path))
    monkeypatch.setattr(
        manager,
        "_get_embedding",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("index_all must not call a provider")
        ),
    )

    assert manager.index_all() == 1
    db = factory()
    row = db.query(NormativaChunk).one()
    assert row.embedding_json is None
    assert len(row.hash_content) == 64
    db.close()


def test_embedding_backfill_clamps_each_run_to_hard_limit(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(normativa_module, "SessionLocal", factory)
    db = factory()
    for index in range(MAX_EMBEDDINGS_PER_RUN + 10):
        db.add(
            NormativaChunk(
                source_file="norma.pdf",
                page=index + 1,
                content=f"fragmento normativo {index}",
                hash_content=f"hash-{index}",
                embedding_json=None,
            )
        )
    db.commit()
    db.close()
    manager = NormativaManager("unused")
    monkeypatch.setattr(manager, "_get_embedding", lambda *_args, **_kwargs: [1.0])

    updated = manager.backfill_embeddings(limit=10_000)
    assert updated == MAX_EMBEDDINGS_PER_RUN
    db = factory()
    assert (
        db.query(NormativaChunk)
        .filter(NormativaChunk.embedding_json.is_(None))
        .count()
        == 10
    )
    db.close()
