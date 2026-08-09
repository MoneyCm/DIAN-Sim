"""One-time bootstrap of the reviewed OPEC 236769 bank in a deployed database."""

from __future__ import annotations

import os


BOOTSTRAP_ENV = "LOAD_CURATED_OPEC236769"


def is_enabled() -> bool:
    return os.getenv(BOOTSTRAP_ENV, "").lower() in {"1", "true", "yes"}


def run_if_enabled() -> dict[str, object] | None:
    """Load reviewed cases only when deployment explicitly requests it."""
    if not is_enabled():
        return None

    from scripts.data.apply_legacy_question_audit import apply_audit
    from scripts.data.repair_curated_macrodomains import repair
    from scripts.data.seed_curated_gap_cases import seed as seed_initial_cases
    from scripts.data.seed_curated_gap_cases_phase10_plus import seed as seed_later_cases

    initial = seed_initial_cases(apply=True)
    later = seed_later_cases(apply=True)
    repaired, domains = repair(apply=True)
    legacy = apply_audit(apply=True)
    return {
        "initial": initial,
        "later": later,
        "macro_domains_repaired": repaired,
        "domains": dict(domains),
        "legacy": legacy,
    }
