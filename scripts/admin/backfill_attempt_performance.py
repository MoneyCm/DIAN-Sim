"""Migra intentos históricos al motor adaptativo.

Por defecto revierte la transacción para mostrar una vista previa. Use
``--apply`` para confirmar después de revisar los conteos.
"""
import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from services.attempt_backfill import backfill_attempt_performance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        result = backfill_attempt_performance(db, args.user_id)
        if args.apply:
            db.commit()
            mode = "APLICADO"
        else:
            db.rollback()
            mode = "VISTA PREVIA"
        print(f"{mode}: {result}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
