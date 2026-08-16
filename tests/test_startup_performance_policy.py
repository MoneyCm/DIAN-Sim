from pathlib import Path


def test_large_question_bank_seed_is_opt_in_not_a_login_side_effect():
    source = Path("app/app.py").read_text(encoding="utf-8-sig")
    maintenance = source.split("def prepare_runtime_catalog", 1)[1].split(
        "prepare_runtime_catalog()", 1
    )[0]

    assert 'os.getenv("AUTO_SEED_OPEC_BANKS"' in maintenance
    assert maintenance.index('os.getenv("AUTO_SEED_OPEC_BANKS"') < maintenance.index(
        "ensure_opec242699_bank()"
    )
    assert "type(catalog_error).__name__" in maintenance


def test_catalog_maintenance_runs_only_after_authentication():
    source = Path("app/app.py").read_text(encoding="utf-8-sig")

    authenticated_branch = source.index(
        "else:\n    # Modo logueado: Montar la app entera y sus funciones"
    )
    runtime_call = source.rindex("\n    prepare_runtime_catalog()")
    assert runtime_call > authenticated_branch
