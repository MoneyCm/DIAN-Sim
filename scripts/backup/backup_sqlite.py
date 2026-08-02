"""Crea un respaldo consistente de la base SQLite local.

Uso: ``python scripts/backup/backup_sqlite.py [destino.db]``
Nunca sobrescribe el origen ni elimina respaldos anteriores.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def backup(source: Path, destination: Path) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if source == destination:
        raise ValueError("El destino debe ser distinto al archivo origen.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", nargs="?", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = root / "dian_sim.db"
    destination = args.destination or root / "backups" / f"dian_sim_{datetime.now():%Y%m%d_%H%M%S}.db"
    print(f"Respaldo creado: {backup(source, destination)}")


if __name__ == "__main__":
    main()
