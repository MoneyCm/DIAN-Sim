from unittest.mock import Mock

from core.generators.llm import LLMGenerator


def test_gemini_case_study_uses_current_stable_model():
    generator = LLMGenerator.__new__(LLMGenerator)
    generator.provider = "gemini"
    generator.model_name = None
    generator.gemini_client = Mock()
    generator.gemini_client.models.generate_content.return_value.text = (
        '{"title":"Caso","text":"Situación",'
        '"questions":[{"stem":"Pregunta",'
        '"options":{"A":"a","B":"b","C":"c"},'
        '"correct_key":"A","rationale":"Razón"}]}'
    )

    result = generator.generate_case_study("Fiscalización aduanera")

    assert result["title"] == "Caso"
    assert generator.gemini_client.models.generate_content.call_args.kwargs["model"] == "gemini-2.5-flash"


def test_gemini_case_study_honors_explicit_model():
    generator = LLMGenerator.__new__(LLMGenerator)
    generator.provider = "gemini"
    generator.model_name = "models/gemini-flash-latest"
    generator.gemini_client = Mock()
    generator.gemini_client.models.generate_content.return_value.text = (
        '{"title":"Caso","text":"Situación","questions":[]}'
    )

    generator.generate_case_study("Régimen cambiario")

    assert generator.gemini_client.models.generate_content.call_args.kwargs["model"] == "gemini-flash-latest"


def test_gemini_audit_reports_the_real_provider_error_without_optional_fallback():
    generator = LLMGenerator.__new__(LLMGenerator)
    generator.provider = "gemini"
    generator.model_name = None
    generator.gemini_client = Mock()
    generator.gemini_client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")
    generator.openai_client = None

    result = generator.audit_question(
        {
            "topic": "Fiscalización",
            "stem": "Pregunta",
            "options_json": {"A": "a", "B": "b", "C": "c"},
            "correct_key": "A",
            "rationale": "Razón",
        },
        source_context="Norma oficial",
    )

    assert result["status"] == "ERROR"
    assert "Gemini unavailable" in result["critique"]
    assert "NoneType" not in result["critique"]
