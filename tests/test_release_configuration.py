"""Static checks for the documented production configuration contract."""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _example_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_environment_example_documents_fail_closed_runtime_flags() -> None:
    values = _example_environment()
    assert values["DIAN_SIM_ENV"] == "development"
    assert values["REQUIRE_DATABASE_URL"] == "false"
    assert values["AUTO_MIGRATE_SCHEMA"] == "false"
    assert values["AUTO_SEED_OPEC_BANKS"] == "false"
    assert "AUTH_COOKIE_SECRET" in values
    assert "DIAN_SIM_FERNET_KEY" in values


def test_environment_example_documents_ai_budgets_and_current_default_model() -> None:
    values = _example_environment()
    expected_budget_keys = {
        "AI_MAX_PROMPT_CHARS",
        "AI_MAX_CALLS_PER_JOB",
        "AI_MAX_CALLS_PER_USER_DAY",
        "AI_MAX_CALLS_GLOBAL_DAY",
        "AI_MAX_INPUT_TOKENS_PER_USER_DAY",
        "AI_MAX_OUTPUT_TOKENS_PER_USER_DAY",
        "AI_MAX_OUTPUT_TOKENS_PER_CALL",
    }
    assert expected_budget_keys <= values.keys()
    assert values["MODEL_FAST"] == "gemini-2.5-flash"
    assert values["MODEL_BALANCED"] == "gemini-2.5-flash"
    assert values["MODEL_REASONING"] == "gemini-2.5-flash"
    assert "gemini-3.6-flash" not in (
        ROOT / "core" / "ai" / "model_router.py"
    ).read_text(encoding="utf-8-sig")
