"""Explicit one-time bootstraps of reviewed OPEC banks in a deployed database."""

from __future__ import annotations

import os


BOOTSTRAP_ENV = "LOAD_CURATED_OPEC236769"
OPEC_241130_BOOTSTRAP_ENV = "LOAD_CURATED_OPEC241130"


def is_enabled(env_name: str = BOOTSTRAP_ENV) -> bool:
    return os.getenv(env_name, "").lower() in {"1", "true", "yes"}


def run_if_enabled() -> dict[str, object] | None:
    """Load reviewed cases only when deployment explicitly requests them."""
    load_236769 = is_enabled()
    load_241130 = is_enabled(OPEC_241130_BOOTSTRAP_ENV)
    if not load_236769 and not load_241130:
        return None

    result: dict[str, object] = {}
    if load_236769:
        from scripts.data.apply_legacy_question_audit import apply_audit
        from scripts.data.repair_curated_macrodomains import repair
        from scripts.data.seed_curated_gap_cases import seed as seed_initial_cases
        from scripts.data.seed_curated_gap_cases_phase10_plus import seed as seed_later_cases

        initial = seed_initial_cases(apply=True)
        later = seed_later_cases(apply=True)
        repaired, domains = repair(apply=True)
        legacy = apply_audit(apply=True)
        result["opec236769"] = {
            "initial": initial,
            "later": later,
            "macro_domains_repaired": repaired,
            "domains": dict(domains),
            "legacy": legacy,
        }
    if load_241130:
        from scripts.data.seed_curated_opec241130 import seed as seed_opec241130

        cases, questions = seed_opec241130(apply=True)
        result["opec241130"] = {"cases": cases, "questions": questions}
    return result
