"""Respaldo, verificación y recuperación segura de una base SQLite local.

El respaldo usa la API online de SQLite (incluye cambios confirmados que estén
en WAL), nunca sobrescribe archivos y crea un manifiesto SHA-256. La
recuperación también escribe en un archivo nuevo: promoverlo al nombre de la
base activa es una decisión operativa posterior, con la aplicación detenida.

Uso compatible con el comando histórico::

    python scripts/backup/backup_sqlite.py [destino.db] [--source origen.db]

Verificación y recuperación::

    python scripts/backup/backup_sqlite.py verify respaldo.db
    python scripts/backup/backup_sqlite.py restore respaldo.db recuperada.db
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TextIO
from urllib.parse import quote


MANIFEST_FORMAT = "dian-sim-sqlite-backup-v1"
RESTORE_RECEIPT_FORMAT = "dian-sim-sqlite-restore-v1"
HASH_CHUNK_SIZE = 1024 * 1024


class BackupValidationError(RuntimeError):
    """El archivo no cumple el contrato verificable de respaldo."""


@dataclass(frozen=True)
class BackupResult:
    database_path: Path
    manifest_path: Path
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class VerificationResult:
    database_path: Path
    manifest_path: Path
    sha256: str
    size_bytes: int
    page_count: int
    user_version: int


@dataclass(frozen=True)
class RestoreResult:
    database_path: Path
    receipt_path: Path
    sha256: str
    size_bytes: int


def manifest_path_for(database_path: Path) -> Path:
    """Return the sidecar path without changing the database suffix."""

    return Path(f"{database_path}.manifest.json")


def restore_receipt_path_for(database_path: Path) -> Path:
    return Path(f"{database_path}.restore.json")


def _require_regular_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError("No existe el archivo SQLite indicado.")
    return resolved


def _readonly_uri(path: Path) -> str:
    # quote keeps query fragments from being interpreted as a URI. Only the
    # local, already resolved file path is accepted.
    encoded = quote(path.as_posix(), safe="/:")
    return f"file:{encoded}?mode=ro"


def _sqlite_metadata(path: Path) -> tuple[int, int]:
    """Run SQLite's full integrity check and return non-sensitive metadata."""

    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as connection:
            rows = tuple(
                str(row[0]).strip().lower()
                for row in connection.execute("PRAGMA integrity_check").fetchall()
            )
            if rows != ("ok",):
                raise BackupValidationError(
                    "La verificación de integridad SQLite falló."
                )
            page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except BackupValidationError:
        raise
    except sqlite3.Error as exc:
        raise BackupValidationError(
            "El archivo indicado no es una base SQLite íntegra."
        ) from exc
    return page_count, user_version


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _reserve_output(path: Path, *, text: bool = False):
    """Atomically reserve an output path; opening with ``x`` never overwrites."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if text:
            return path.open("x+", encoding="utf-8", newline="\n")
        return path.open("x+b")
    except FileExistsError as exc:
        raise FileExistsError(
            "El destino o su archivo de verificación ya existe; no se sobrescribió."
        ) from exc


def _cleanup_created(paths: Iterable[Path]) -> None:
    # These paths were created exclusively by this process. Cleanup never
    # targets a pre-existing file because _reserve_output uses mode ``x``.
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _write_json(handle: TextIO, payload: dict[str, object]) -> None:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()


def create_backup(source: Path, destination: Path) -> BackupResult:
    """Create a consistent, integrity-checked backup and SHA-256 manifest."""

    source = _require_regular_file(source)
    destination = destination.expanduser().resolve()
    manifest = manifest_path_for(destination)
    if source == destination:
        raise ValueError("El destino debe ser distinto al archivo origen.")

    # Refuse corrupt input before reserving any output.
    _sqlite_metadata(source)

    created: list[Path] = []
    destination_handle = None
    manifest_handle = None
    try:
        destination_handle = _reserve_output(destination)
        created.append(destination)
        manifest_handle = _reserve_output(manifest, text=True)
        created.append(manifest)
        destination_handle.close()
        destination_handle = None

        # SQLite's online backup API reads a coherent snapshot, including WAL.
        with sqlite3.connect(_readonly_uri(source), uri=True) as src:
            with sqlite3.connect(destination) as dst:
                src.backup(dst)

        page_count, user_version = _sqlite_metadata(destination)
        size_bytes = destination.stat().st_size
        digest = sha256_file(destination)
        _write_json(
            manifest_handle,
            {
                "backup_file": destination.name,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "format": MANIFEST_FORMAT,
                "integrity_check": "ok",
                "page_count": page_count,
                "sha256": digest,
                "size_bytes": size_bytes,
                "sqlite_user_version": user_version,
            },
        )
        manifest_handle.close()
        manifest_handle = None
    except Exception:
        if destination_handle is not None:
            destination_handle.close()
        if manifest_handle is not None:
            manifest_handle.close()
        _cleanup_created(reversed(created))
        raise

    return BackupResult(destination, manifest, digest, size_bytes)


def backup(source: Path, destination: Path) -> Path:
    """Backward-compatible wrapper returning only the database path."""

    return create_backup(source, destination).database_path


def verify_backup(
    database_path: Path,
    manifest_path: Path | None = None,
) -> VerificationResult:
    """Verify sidecar contract, size, SHA-256 and full SQLite integrity."""

    database = _require_regular_file(database_path)
    manifest = _require_regular_file(manifest_path or manifest_path_for(database))
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupValidationError("El manifiesto del respaldo no es válido.") from exc

    if not isinstance(payload, dict) or payload.get("format") != MANIFEST_FORMAT:
        raise BackupValidationError("El formato del manifiesto no es reconocido.")
    if payload.get("backup_file") != database.name:
        raise BackupValidationError("El manifiesto no corresponde a este respaldo.")

    expected_size = payload.get("size_bytes")
    expected_hash = str(payload.get("sha256") or "").lower()
    actual_size = database.stat().st_size
    actual_hash = sha256_file(database)
    if not isinstance(expected_size, int) or expected_size != actual_size:
        raise BackupValidationError("El tamaño del respaldo no coincide con el manifiesto.")
    if len(expected_hash) != 64 or not hmac.compare_digest(expected_hash, actual_hash):
        raise BackupValidationError("El SHA-256 del respaldo no coincide con el manifiesto.")

    page_count, user_version = _sqlite_metadata(database)
    if payload.get("integrity_check") != "ok":
        raise BackupValidationError("El manifiesto no registra una copia íntegra.")
    if payload.get("page_count") != page_count:
        raise BackupValidationError("La cantidad de páginas no coincide con el manifiesto.")
    if payload.get("sqlite_user_version") != user_version:
        raise BackupValidationError("La versión SQLite no coincide con el manifiesto.")
    return VerificationResult(
        database,
        manifest,
        actual_hash,
        actual_size,
        page_count,
        user_version,
    )


def restore_backup(
    backup_path: Path,
    destination: Path,
    manifest_path: Path | None = None,
) -> RestoreResult:
    """Restore a verified backup into a new path and write an audit receipt."""

    verified = verify_backup(backup_path, manifest_path)
    destination = destination.expanduser().resolve()
    receipt = restore_receipt_path_for(destination)
    if verified.database_path == destination:
        raise ValueError("El destino restaurado debe ser distinto al respaldo.")

    created: list[Path] = []
    destination_handle = None
    receipt_handle = None
    try:
        destination_handle = _reserve_output(destination)
        created.append(destination)
        receipt_handle = _reserve_output(receipt, text=True)
        created.append(receipt)
        destination_handle.close()
        destination_handle = None

        with sqlite3.connect(_readonly_uri(verified.database_path), uri=True) as src:
            with sqlite3.connect(destination) as dst:
                src.backup(dst)

        page_count, user_version = _sqlite_metadata(destination)
        digest = sha256_file(destination)
        size_bytes = destination.stat().st_size
        _write_json(
            receipt_handle,
            {
                "backup_file": verified.database_path.name,
                "backup_sha256": verified.sha256,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "format": RESTORE_RECEIPT_FORMAT,
                "integrity_check": "ok",
                "page_count": page_count,
                "restored_file": destination.name,
                "restored_sha256": digest,
                "size_bytes": size_bytes,
                "sqlite_user_version": user_version,
            },
        )
        receipt_handle.close()
        receipt_handle = None
    except Exception:
        if destination_handle is not None:
            destination_handle.close()
        if receipt_handle is not None:
            receipt_handle.close()
        _cleanup_created(reversed(created))
        raise

    return RestoreResult(destination, receipt, digest, size_bytes)


def _backup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path)
    parser.add_argument(
        "--source",
        type=Path,
        help="SQLite origen. Por defecto usa dian_sim.db en el repositorio.",
    )
    return parser


def _verify_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica un respaldo SQLite.")
    parser.add_argument("database", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser


def _restore_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restaura un respaldo verificado.")
    parser.add_argument("database", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if arguments and arguments[0] == "verify":
            args = _verify_parser().parse_args(arguments[1:])
            result = verify_backup(args.database, args.manifest)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "database": str(result.database_path),
                        "manifest": str(result.manifest_path),
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if arguments and arguments[0] == "restore":
            args = _restore_parser().parse_args(arguments[1:])
            result = restore_backup(args.database, args.destination, args.manifest)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "database": str(result.database_path),
                        "receipt": str(result.receipt_path),
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        args = _backup_parser().parse_args(arguments)
        source = args.source or root / "dian_sim.db"
        destination = args.destination or (
            root
            / "backups"
            / f"dian_sim_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
        )
        result = create_backup(source, destination)
        print(
            json.dumps(
                {
                    "ok": True,
                    "database": str(result.database_path),
                    "manifest": str(result.manifest_path),
                    "sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (BackupValidationError, FileExistsError, FileNotFoundError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
