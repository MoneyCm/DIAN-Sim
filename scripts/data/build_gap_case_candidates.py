"""Build source-grounded GOA candidates without mutating the question bank."""

import argparse
import json
from pathlib import Path

from core.config import get_api_key
from core.generators.llm import LLMGenerator


CUSTOMS_SOURCE = """
Fuente oficial: Compilación Jurídica DIAN, Decreto 1165 de 2019.
Artículo 581: el control posterior se ejerce después de la nacionalización o de
finalizar el régimen; permite comprobar obligación aduanera, exactitud de las
declaraciones, requisitos del régimen y documentos comerciales mediante
comprobaciones, estudios e investigaciones.
Artículos 590 y 591: la DIAN desarrolla investigaciones y controles y cuenta
con facultades de fiscalización para asegurar el cumplimiento aduanero.
Artículo 593: ante indicios de inexactitud o infracción con sanción monetaria,
la DIAN puede emplazar al usuario para que dentro del mes siguiente presente
la declaración procedente, liquide y pague tributos, intereses, sanción o
rescate, o se allane a la sanción con la reducción aplicable.
No uses otros artículos, cifras, plazos ni consecuencias.
""".strip()


EXCHANGE_SOURCE = """
Fuente oficial: Compilación Jurídica DIAN, Decreto-Ley 2245 de 2011.
Artículo 2: una infracción cambiaria es una contravención administrativa de
las disposiciones cambiarias vigentes al momento de la transgresión.
Artículo 3 numeral 1: no presentar oportunamente la declaración de cambio,
presentarla con datos equivocados, no exhibirla con soportes, no conservarla o
no transmitirla cuando corresponde a una cuenta de compensación genera multa
de 25 UVT por declaración, con máximo de 1.000 UVT por investigación.
Artículo 3 numeral 7: canalizar como importación, exportación o financiación
montos que no se derivan de esas operaciones genera multa del 100% del valor.
Artículo 3 numeral 8: canalizar un valor superior al documento aduanero genera
una multa del 100% de la diferencia, salvo diferencia justificada y probada.
Artículo 3 numeral 24: realizar pagos, giros, remesas o transferencias desde o
hacia el país sin autorización genera multa del 100% de cada operación.
No uses otras infracciones, cifras, plazos ni autoridades.
""".strip()


SPECS = [
    ("aduanas_control_posterior", "Control posterior: contraste entre declaración, factura y registros contables", CUSTOMS_SOURCE),
    ("aduanas_requisitos_regimen", "Control posterior: incumplimiento de requisitos del régimen de importación", CUSTOMS_SOURCE),
    ("aduanas_gestion_persuasiva", "Gestión persuasiva ante inexactitud de una declaración aduanera", CUSTOMS_SOURCE),
    ("aduanas_revision_documental", "Fiscalización aduanera: documentos comerciales y exactitud de declaraciones", CUSTOMS_SOURCE),
    ("cambiario_declaracion", "Control cambiario: declaración de cambio y conservación de soportes", EXCHANGE_SOURCE),
    ("cambiario_canalizacion", "Control cambiario: canalización de valores y diferencias justificadas", EXCHANGE_SOURCE),
    ("cambiario_transferencias", "Control cambiario: transferencias internacionales no autorizadas", EXCHANGE_SOURCE),
]


def structural_errors(case: dict) -> list[str]:
    errors = []
    questions = case.get("questions") or []
    if len(questions) != 3:
        errors.append("El caso no contiene exactamente tres preguntas")
    for index, question in enumerate(questions, start=1):
        options = question.get("options") or {}
        if set(options) != {"A", "B", "C"}:
            errors.append(f"P{index}: opciones distintas de A/B/C")
        if question.get("correct_key") not in options:
            errors.append(f"P{index}: clave inválida")
        if not question.get("rationale") or not question.get("source_ref"):
            errors.append(f"P{index}: falta justificación o fuente")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scratch/gap_cases_phase1.json")
    parser.add_argument("--limit", type=int, default=len(SPECS))
    args = parser.parse_args()

    generator = LLMGenerator("gemini", get_api_key("gemini"))
    results = []
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    for slug, topic, source in SPECS[: args.limit]:
        print(f"GENERATING {slug}", flush=True)
        case = generator.generate_case_study(topic, 3, 3, source)
        errors = structural_errors(case)
        audits = []
        if not errors:
            payload = {
                "case_text": case.get("text", ""),
                "topic": case.get("topic", topic),
                "stem": json.dumps(case.get("questions", []), ensure_ascii=False),
                "options_json": "Auditar las tres preguntas como bloque",
                "correct_key": "Claves incluidas en el bloque",
                "rationale": "Revisar cada clave, distractor y fuente",
            }
            audits.append(generator.audit_question(payload, source))
        approved = not errors and len(audits) == 1 and (
            audits[0].get("status") == "APPROVED"
            and float(audits[0].get("score", 0)) >= 9
        )
        results.append({
            "slug": slug,
            "source_context": source,
            "case": case,
            "structural_errors": errors,
            "audits": audits,
            "machine_approved": approved,
            "manual_reviewed": False,
        })
        print(f"RESULT {slug}: {'PASS' if approved else 'REVIEW'}", flush=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {output} ({len(results)} candidates)")


if __name__ == "__main__":
    main()
