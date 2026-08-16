from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.backup.backup_sqlite import (
    BackupValidationError,
    MANIFEST_FORMAT,
    RESTORE_RECEIPT_FORMAT,
    create_backup,
    main,
    manifest_path_for,
    restore_backup,
    restore_receipt_path_for,
    sha256_file,
    verify_backup,
)


def _create_database(path: Path, *, wal: bool = False) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    if wal:
        connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO records(value) VALUES ('dato verificable')")
    connection.execute("PRAGMA user_version=7")
    connection.commit()
    return connection


def _values(path: Path) -> list[str]:
    with sqlite3.connect(path) as connection:
        return [row[0] for row in connection.execute("SELECT value FROM records")]


def test_backup_captures_committed_wal_and_writes_verifiable_manifest(tmp_path: Path):
    source = tmp_path / "source.db"
    writer = _create_database(source, wal=True)
    writer.execute("INSERT INTO records(value) VALUES ('todavía en WAL')")
    writer.commit()
    destination = tmp_path / "backup.db"

    try:
        result = create_backup(source, destination)
    finally:
        writer.close()

    assert result.database_path == destination.resolve()
    assert result.manifest_path == manifest_path_for(destination.resolve())
    assert _values(destination) == ["dato verificable", "todavía en WAL"]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["format"] == MANIFEST_FORMAT
    assert manifest["backup_file"] == "backup.db"
    assert manifest["integrity_check"] == "ok"
    assert manifest["sqlite_user_version"] == 7
    assert manifest["sha256"] == sha256_file(destination)
    assert manifest["size_bytes"] == destination.stat().st_size

    verified = verify_backup(destination)
    assert verified.sha256 == result.sha256
    assert verified.user_version == 7


def test_backup_never_overwrites_destination_or_existing_manifest(tmp_path: Path):
    source = tmp_path / "source.db"
    _create_database(source).close()
    destination = tmp_path / "existing.db"
    destination.write_bytes(b"contenido que debe conservarse")

    with pytest.raises(FileExistsError):
        create_backup(source, destination)
    assert destination.read_bytes() == b"contenido que debe conservarse"

    destination.unlink()
    manifest = manifest_path_for(destination)
    manifest.write_text("manifiesto previo", encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_backup(source, destination)
    assert not destination.exists()
    assert manifest.read_text(encoding="utf-8") == "manifiesto previo"


def test_corrupt_source_is_rejected_without_leaving_outputs(tmp_path: Path):
    source = tmp_path / "not-a-database.db"
    source.write_bytes(b"esto no es SQLite")
    destination = tmp_path / "backup.db"

    with pytest.raises(BackupValidationError):
        create_backup(source, destination)

    assert not destination.exists()
    assert not manifest_path_for(destination).exists()


def test_verify_detects_tampering_before_restore(tmp_path: Path):
    source = tmp_path / "source.db"
    _create_database(source).close()
    backup_path = tmp_path / "backup.db"
    create_backup(source, backup_path)

    with backup_path.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(BackupValidationError, match="tamaño"):
        verify_backup(backup_path)
    with pytest.raises(BackupValidationError):
        restore_backup(backup_path, tmp_path / "restored.db")
    assert not (tmp_path / "restored.db").exists()


def test_restore_round_trip_uses_new_file_and_emits_receipt(tmp_path: Path):
    source = tmp_path / "source.db"
    _create_database(source).close()
    backup_path = tmp_path / "backup.db"
    backup_result = create_backup(source, backup_path)
    restored = tmp_path / "restored.db"

    result = restore_backup(backup_path, restored)

    assert _values(restored) == ["dato verificable"]
    assert result.database_path == restored.resolve()
    assert result.receipt_path == restore_receipt_path_for(restored.resolve())
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["format"] == RESTORE_RECEIPT_FORMAT
    assert receipt["integrity_check"] == "ok"
    assert receipt["backup_sha256"] == backup_result.sha256
    assert receipt["restored_sha256"] == sha256_file(restored)


def test_restore_never_overwrites_destination_or_receipt(tmp_path: Path):
    source = tmp_path / "source.db"
    _create_database(source).close()
    backup_path = tmp_path / "backup.db"
    create_backup(source, backup_path)
    destination = tmp_path / "restored.db"
    destination.write_bytes(b"base existente")

    with pytest.raises(FileExistsError):
        restore_backup(backup_path, destination)
    assert destination.read_bytes() == b"base existente"

    destination.unlink()
    receipt = restore_receipt_path_for(destination)
    receipt.write_text("recibo anterior", encoding="utf-8")
    with pytest.raises(FileExistsError):
        restore_backup(backup_path, destination)
    assert not destination.exists()
    assert receipt.read_text(encoding="utf-8") == "recibo anterior"


def test_manifest_does_not_record_source_path_or_environment_secrets(tmp_path: Path):
    secret_directory = tmp_path / "postgres-password-should-not-appear"
    secret_directory.mkdir()
    source = secret_directory / "source.db"
    _create_database(source).close()
    destination = tmp_path / "backup.db"

    result = create_backup(source, destination)
    text = result.manifest_path.read_text(encoding="utf-8")

    assert str(source.resolve()) not in text
    assert "postgres-password-should-not-appear" not in text
    assert "DATABASE_URL" not in text


def test_cli_verify_returns_nonzero_for_a_tampered_manifest(tmp_path: Path, capsys):
    source = tmp_path / "source.db"
    _create_database(source).close()
    destination = tmp_path / "backup.db"
    result = create_backup(source, destination)
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    payload["sha256"] = "0" * 64
    result.manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["verify", str(destination)]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert "postgres-password" not in output["error"]
