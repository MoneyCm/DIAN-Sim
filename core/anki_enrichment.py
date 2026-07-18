from __future__ import annotations

import datetime
import hashlib
import json
from typing import Callable, Optional

from google.genai import types
from sqlalchemy.orm import Session

from core.generators.llm import LLMGenerator
from core.generators.utils import repair_and_parse_json
from db.models import Question, QuestionAnkiEnrichment

PROMPT_VERSION = "v1"
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-flash-latest",
    "groq": "llama-3.3-70b-versatile",
    "mistral": "mistral-small-latest",
}


def question_source_hash(question: Question) -> str:
    payload = {
        "stem": question.stem,
        "options": question.options_json or {},
        "correct_key": question.correct_key,
        "rationale": question.rationale,
        "source_refs": question.source_refs,
        "prompt_version": PROMPT_VERSION,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def needs_enrichment(question: Question, force: bool = False) -> bool:
    enrichment = question.anki_enrichment
    if force:
        return not enrichment or enrichment.status != "reviewed"
    if not enrichment:
        return True
    if enrichment.status not in {"generated", "reviewed"}:
        return True
    return enrichment.source_hash != question_source_hash(question) or enrichment.prompt_version != PROMPT_VERSION


def build_enrichment_prompt(question: Question) -> str:
    options = question.options_json or {}
    return f"""
Actúa como preparador experto para concursos de la DIAN y crea material de repetición espaciada.
Analiza la pregunta y responde EXCLUSIVAMENTE con un objeto JSON válido con estas claves:
- rule: la regla decisiva, concreta y memorizable (máximo 60 palabras).
- exception: la excepción, límite o condición que más podría cambiar la respuesta (máximo 60 palabras). Si no existe una excepción verificable, indica "No identificada en la fuente".
- distractor: explica cuál distractor es el más atractivo y por qué es incorrecto (máximo 80 palabras).

No inventes artículos, plazos ni excepciones. Usa solamente la pregunta, su justificación y referencia.

TEMA: {question.topic}
PREGUNTA: {question.stem}
OPCIONES: {json.dumps(options, ensure_ascii=False)}
RESPUESTA CORRECTA: {question.correct_key}
JUSTIFICACIÓN: {question.rationale or "Sin justificación"}
REFERENCIA: {question.source_refs or "Sin referencia"}
""".strip()


def _call_llm(provider: str, api_key: str, model: Optional[str], prompt: str) -> tuple[dict, str]:
    provider = provider.lower()
    selected_model = model or DEFAULT_MODELS.get(provider)
    generator = LLMGenerator(provider, api_key, model_name=selected_model, goa_mode=False)

    if provider in {"openai", "groq"} and generator.openai_client:
        response = generator.openai_client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "Responde únicamente JSON válido."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    elif provider == "mistral" and generator.mistral_client:
        response = generator.mistral_client.chat.complete(
            model=selected_model,
            messages=[
                {"role": "system", "content": "Responde únicamente JSON válido."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    elif provider == "gemini" and generator.gemini_client:
        config = types.GenerateContentConfig(response_mime_type="application/json")
        response = generator.gemini_client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=config,
        )
        content = response.text
    else:
        raise ValueError(f"Proveedor sin cliente disponible: {provider}")

    data = repair_and_parse_json(content)
    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió un objeto JSON válido")
    return data, selected_model


def enrich_question(
    db: Session,
    question: Question,
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    force: bool = False,
    generator: Optional[Callable[[str], dict]] = None,
) -> QuestionAnkiEnrichment:
    if not api_key and generator is None:
        raise ValueError("Se requiere una API key para generar el enriquecimiento Anki")

    source_hash = question_source_hash(question)
    enrichment = question.anki_enrichment
    if enrichment and enrichment.status == "reviewed" and not force:
        return enrichment
    if not needs_enrichment(question, force=force):
        return enrichment

    if enrichment is None:
        enrichment = QuestionAnkiEnrichment(
            question_id=question.question_id,
            source_hash=source_hash,
            prompt_version=PROMPT_VERSION,
            status="pending",
        )
        db.add(enrichment)
        db.flush()

    enrichment.status = "processing"
    enrichment.attempt_count = (enrichment.attempt_count or 0) + 1
    enrichment.error_message = None
    db.commit()

    try:
        prompt = build_enrichment_prompt(question)
        if generator:
            data = generator(prompt)
            selected_model = model or "test-generator"
        else:
            data, selected_model = _call_llm(provider, api_key, model, prompt)

        rule = str(data.get("rule", "")).strip()
        exception = str(data.get("exception", "")).strip()
        distractor = str(data.get("distractor", "")).strip()
        if not rule or not exception or not distractor:
            raise ValueError("La respuesta debe incluir rule, exception y distractor")

        enrichment.rule = rule
        enrichment.exception = exception
        enrichment.distractor = distractor
        enrichment.status = "generated"
        enrichment.source_hash = source_hash
        enrichment.model = selected_model
        enrichment.prompt_version = PROMPT_VERSION
        enrichment.generated_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        enrichment.error_message = None
        db.commit()
        db.refresh(enrichment)
        return enrichment
    except Exception as exc:
        enrichment.status = "error"
        enrichment.error_message = str(exc)[:2000]
        db.commit()
        raise


def backfill_enrichments(
    session_factory,
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    batch_size: int = 10,
    limit: Optional[int] = None,
    force: bool = False,
    progress_callback=None,
) -> dict:
    db = session_factory()
    try:
        questions = db.query(Question).order_by(Question.created_at.asc()).all()
        pending = [q for q in questions if needs_enrichment(q, force=force)]
        if limit:
            pending = pending[:limit]
        total = len(pending)
        generated = 0
        errors = 0

        for index, question in enumerate(pending, start=1):
            try:
                enrich_question(db, question, provider, api_key, model=model, force=force)
                generated += 1
            except Exception:
                errors += 1
            if progress_callback:
                progress_callback(int(index * 100 / max(total, 1)), f"{index}/{total} procesadas")
            if batch_size and index % batch_size == 0:
                db.expire_all()

        return {"total": total, "generated": generated, "errors": errors}
    finally:
        db.close()