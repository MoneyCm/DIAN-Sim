"""Idempotent canonical verification for OPEC 236769 batch 2.

This migration approves only 29 questions that were already labelled
``human_source_grounded`` and whose answer keys were checked against the
current official text.  Three semantically redundant candidates remain
untouched and every other unverified question stays outside canonical
delivery.

Usage:
    python migrations/apply_canonical_batch2_2026-08-21.py [--dry-run]
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.engine import editorial_question_difficulty
from core.question_quality import audit_question_structure
from core.question_revision import question_revision_hash
from db.models import (
    OpecProfile,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
    SourceDocument,
)
from db.session import SessionLocal


NOW = datetime.datetime(2026, 8, 21, 21, 0, 0)
ACTOR = "codex/canonical-source-review-batch2-2026-08-21"

SOURCE_DOCS = {
    "ESTATUTO-TRIBUTARIO": {
        "title": "Estatuto Tributario (Decreto 624 de 1989)",
        "entity": "DIAN",
        "document_type": "norma",
        "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
    },
    "DECRETO-1165-2019": {
        "title": "Decreto 1165 de 2019",
        "entity": "DIAN",
        "document_type": "norma",
        "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1165_2019.htm",
    },
    "LEY-1437-2011": {
        "title": "Ley 1437 de 2011 - CPACA",
        "entity": "Congreso de la Republica",
        "document_type": "norma",
        "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/ley_1437_2011.htm",
    },
    "CONCEPTO-DIAN-18477-2025": {
        "title": "Concepto DIAN 018477 interno 2191 de 2025",
        "entity": "DIAN",
        "document_type": "doctrina",
        "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_18477_2025.htm",
        "issued_at": datetime.date(2025, 11, 19),
    },
    "PR-COT-0432": {
        "title": "Liquidacion Provisional",
        "entity": "DIAN",
        "document_type": "procedimiento",
        "official_url": "https://www.dian.gov.co/atencionciudadano/LMDP/Cumplimiento-Obligaciones-Tributarias/Fiscalizacion-y-Liquidacion/Procedimientos/PR-COT-0432.pdf",
        "version": "3",
        "valid_from": datetime.date(2025, 2, 24),
    },
}


# qid, function_number, source_document_key, exact locator, short official excerpt
CITATIONS = [
    # F8 - practica y valoracion de pruebas
    ("9d1081e7-f6b3-4e7d-b0aa-c577cfa7b856", 8, "ESTATUTO-TRIBUTARIO", "Art. 742",
     "La determinación de tributos y la imposición de sanciones deben fundarse en los hechos que aparezcan demostrados en el respectivo expediente."),
    ("23c4dfe9-4eeb-4ee8-b522-5cbded742acc", 8, "ESTATUTO-TRIBUTARIO", "Art. 745",
     "Las dudas provenientes de vacíos probatorios [...] deben resolverse, si no hay modo de eliminarlas, a favor del contribuyente."),
    ("8ae28dc5-9684-4a1c-a8e8-3e06d5a7b6ec", 8, "ESTATUTO-TRIBUTARIO", "Art. 745",
     "Las dudas provenientes de vacíos probatorios [...] deben resolverse, si no hay modo de eliminarlas, a favor del contribuyente."),
    ("a7862e00-678f-4c7d-8c38-eece7c8aec53", 8, "ESTATUTO-TRIBUTARIO", "Art. 687",
     "Las apreciaciones del contribuyente o de terceros [...] no son obligatorias para éstas."),

    # F4 - actos administrativos y procedimiento
    ("595fe757-8c33-4a2d-8321-6cece57fb149", 4, "LEY-1437-2011", "Art. 21, inciso final",
     "Los términos para decidir o responder se contarán a partir del día siguiente a la recepción de la Petición por la autoridad competente."),
    ("8ea1e752-43e4-416b-a281-4c7c257485e3", 4, "LEY-1437-2011", "Art. 42",
     "La decisión [...] será motivada. La decisión resolverá todas las peticiones que hayan sido oportunamente planteadas."),
    ("5c3bde1e-26a4-4aa5-bef1-aacd772992ec", 4, "ESTATUTO-TRIBUTARIO", "Art. 566-1, inciso 3",
     "La notificación electrónica se entenderá surtida para todos los efectos legales, en la fecha del envío del acto administrativo."),
    ("950343c0-2923-4917-af42-b416dba9a377", 4, "CONCEPTO-DIAN-18477-2025", "Tesis juridica y nums. 5, 12 y 14",
     "El término de cinco (5) días [...] se contabiliza a partir del día siguiente de la entrega del correo electrónico de notificación."),
    ("ac20018a-3410-4628-834a-7a4182e8c2f3", 4, "LEY-1437-2011", "Art. 40",
     "El interesado contará con la oportunidad de controvertir las pruebas [...] antes de que se dicte una decisión de fondo."),
    ("dbc99ba0-c1d7-4a8d-b345-d82a7eef9594", 4, "LEY-1437-2011", "Art. 21",
     "Dentro del término señalado remitirá la petición al competente y enviará copia del oficio remisorio al peticionario."),
    ("e354d6a8-deeb-4783-907c-75ed46f4e9f4", 4, "LEY-1437-2011", "Art. 12, inciso 4",
     "La actuación administrativa se suspenderá desde la manifestación del impedimento [...] hasta cuando se decida."),
    ("de147e2c-8002-4f39-adf4-aa0b13f5949b", 4, "LEY-1437-2011", "Art. 40",
     "Hasta antes de que se profiera la decisión de fondo se podrán aportar, pedir y practicar pruebas."),
    ("e7f4ff44-fb0f-444a-bb9a-7ffbbd478db7", 4, "LEY-1437-2011", "Art. 12, inciso 1",
     "El servidor enviará dentro de los tres (3) días siguientes a su conocimiento la actuación con escrito motivado al superior."),
    ("ed45d57d-bc70-49d4-a44b-ea5e7b36fa3a", 4, "LEY-1437-2011", "Art. 11, numeral 1",
     "Tener interés particular y directo en [...] el asunto, o tenerlo su cónyuge, compañero o compañera permanente."),
    ("f6e7caae-be17-4474-b454-703176f56425", 4, "ESTATUTO-TRIBUTARIO", "Art. 722, literales a, b y c",
     "Que se formule por escrito [...] Que se interponga dentro de la oportunidad legal [...] o se acredite la personería."),
    ("ff14c876-903f-4675-a3ec-821501188f98", 4, "LEY-1437-2011", "Art. 21, inciso 2",
     "En caso de no existir funcionario competente así se lo comunicará."),

    # F5 - revision tecnica y juridica
    ("7959d859-10e3-4014-ad9c-a4a42344bf75", 5, "PR-COT-0432", "pp. 3 y 10 del documento (PDF pp. 2 y 9), actividades 8 y 9",
     "Dentro del término de dos (2) meses siguientes [...] Luego de revisada la Liquidación Provisional, esta es pasada para su aprobación y firma."),

    # F6 - ejecucion de acciones de fiscalizacion
    ("9762be42-43e4-4b7e-8c94-5c9a7350a02c", 6, "ESTATUTO-TRIBUTARIO", "Art. 684, literales a, c, d y e",
     "Verificar la exactitud de las declaraciones [...] Exigir [...] documentos [...] Ordenar la exhibición y examen parcial de los libros, comprobantes y documentos."),
    ("9a02fae3-0687-4e5f-8381-1bb082972711", 6, "ESTATUTO-TRIBUTARIO", "Art. 779, inciso 3",
     "Se levantará un acta que contenga todos los hechos, pruebas y fundamentos en que se sustenta."),
    ("198672c7-28b5-4f67-9946-0fb69679d010", 6, "DECRETO-1165-2019", "Art. 581, incisos 1 y 2",
     "Buscan establecer [...] la exactitud de los datos consignados en declaraciones aduaneras presentadas durante un determinado período de tiempo."),
    ("2a58a9e2-c55d-49cc-8d44-f527f346ccd7", 6, "DECRETO-1165-2019", "Art. 581, incisos 1 y 2",
     "El control se llevará a cabo sobre las mercancías, los documentos relativos a las operaciones comerciales [...] mediante comprobaciones, estudios o investigaciones."),
    ("74ab6e63-2575-4d8e-9d5f-3cfa1080eaa4", 6, "ESTATUTO-TRIBUTARIO", "Art. 260-4, paragrafo",
     "En caso de existir comparables internos, el contribuyente deberá tomarlos en cuenta de manera prioritaria."),
    ("6314a453-d4de-44ed-b12a-af51bc09e4da", 6, "ESTATUTO-TRIBUTARIO", "Art. 779, inciso 2",
     "Debiéndose en él indicar los hechos materia de la prueba y los funcionarios comisionados para practicarla."),
    ("842d7fde-7ba5-4512-b43e-e9113253f33b", 6, "ESTATUTO-TRIBUTARIO", "Art. 260-5, inciso 2",
     "Patrimonio bruto [...] igual o superior [...] a cien mil (100.000) UVT o [...] ingresos brutos [...] a sesenta y un mil (61.000) UVT."),
    ("a4023c31-bb25-415f-9940-4d6446936e36", 6, "DECRETO-1165-2019", "Art. 591, numeral 3",
     "Verificar la exactitud de las declaraciones, documentos soporte u otros informes, cuando lo considere necesario."),
    ("abfb43b8-8499-46cd-9ac5-7885bddc893b", 6, "ESTATUTO-TRIBUTARIO", "Art. 260-5, inciso 3",
     "La información financiera y contable [...] deberá estar firmada por el representante legal y el contador público o revisor fiscal respectivo."),
    ("afcad13b-a88e-4eaa-a4e6-014d0fae4a1b", 6, "ESTATUTO-TRIBUTARIO", "Arts. 683 y 684, literal f",
     "Efectuar todas las diligencias necesarias para la correcta y oportuna determinación [...] facilitando al contribuyente la aclaración de toda duda u omisión."),
    ("b49aba7d-f513-4295-8385-d9686bbb75d7", 6, "ESTATUTO-TRIBUTARIO", "Art. 260-4, paragrafo",
     "En caso de existir comparables internos, el contribuyente deberá tomarlos en cuenta de manera prioritaria."),
    ("bc3ac266-0bd3-4ffc-882d-9023f6aa68ab", 6, "ESTATUTO-TRIBUTARIO", "Art. 260-5, inciso 2",
     "Deberán preparar y enviar la documentación comprobatoria que contenga un informe maestro [...] y un informe local."),
]


CONTENT_PATCHES = {
    "74ab6e63-2575-4d8e-9d5f-3cfa1080eaa4": {
        "rationale": "Los comparables internos deben considerarse prioritariamente cuando existen.",
        "source_refs": "Estatuto Tributario, articulo 260-4, paragrafo (Compilacion Juridica DIAN).",
    },
    "b49aba7d-f513-4295-8385-d9686bbb75d7": {
        "rationale": "Cuando existen comparables internos, el paragrafo del articulo 260-4 ordena considerarlos prioritariamente.",
        "source_refs": "Estatuto Tributario, articulo 260-4, paragrafo (Compilacion Juridica DIAN).",
    },
}


EXCLUDED_REDUNDANT_QIDS = {
    "5678fed2-1f03-43fe-b332-5cc2cd8d27f4",
    "99865a70-efe6-4c69-a5df-d98c80e0ae71",
    "06fc026c-f560-4dca-9768-1f04bb74cbde",
}

BATCH_QIDS = [row[0] for row in CITATIONS]


def _source_doc(db, document_key):
    return db.query(SourceDocument).filter_by(document_key=document_key).first()


def _already_correct(question, citation, db, profile_id):
    qid, _function_number, document_key, locator, excerpt = citation
    patch = CONTENT_PATCHES.get(qid, {})
    if not question.is_verified:
        return False
    if any(getattr(question, field) != value for field, value in patch.items()):
        return False

    report = question.quality_report if isinstance(question.quality_report, dict) else {}
    verification = report.get("source_verification") or {}
    source_doc = _source_doc(db, document_key)
    if source_doc is None:
        return False
    expected_verification = {
        "status": "official_current",
        "url": source_doc.official_url,
        "locator": locator,
        "supporting_excerpt": excerpt,
    }
    if any(verification.get(key) != value for key, value in expected_verification.items()):
        return False
    if not verification.get("verified_on") or not verification.get("verified_by"):
        return False
    if report.get("review") != "source_grounded":
        return False

    difficulty = editorial_question_difficulty(question)
    expected_hash = question_revision_hash(question, difficulty)
    revision = (
        db.query(QuestionRevision)
        .filter_by(question_id=qid)
        .order_by(QuestionRevision.revision_number.desc())
        .first()
    )
    if (
        revision is None
        or revision.status != "approved"
        or revision.bank_partition != "training"
        or revision.content_hash != expected_hash
    ):
        return False

    scope = db.query(QuestionOpecScope).filter_by(
        question_id=qid,
        opec_profile_id=profile_id,
    ).first()
    if scope is None or scope.bank_partition != "training":
        return False

    citations = (
        db.query(QuestionCitation)
        .filter_by(question_id=qid, source_document_id=source_doc.id)
        .all()
    )
    return any(
        item.locator == locator
        and item.excerpt == excerpt
        and item.supports_key
        and item.verified_at
        and str(item.verified_by or "").strip()
        for item in citations
    )


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        profile = db.query(OpecProfile).filter_by(opec_number="236769").first()
        if profile is None:
            raise RuntimeError("No existe el perfil OPEC 236769.")

        print("=== Canonical Verification Batch 2 (idempotent) ===")

        source_updates = 0
        for document_key, metadata in SOURCE_DOCS.items():
            document = _source_doc(db, document_key)
            if document is None:
                source_updates += 1
                if dry_run:
                    print(f"  [dry-run] Would create source {document_key}")
                    continue
                document = SourceDocument(
                    document_key=document_key,
                    title=metadata["title"],
                    entity=metadata["entity"],
                    document_type=metadata["document_type"],
                    official_url=metadata["official_url"],
                    version=metadata.get("version"),
                    issued_at=metadata.get("issued_at"),
                    valid_from=metadata.get("valid_from"),
                    validity_status="current",
                    last_verified_at=NOW,
                )
                db.add(document)
                continue
            changed = (
                document.official_url != metadata["official_url"]
                or document.validity_status != "current"
            )
            if changed:
                source_updates += 1
                if not dry_run:
                    document.official_url = metadata["official_url"]
                    document.validity_status = "current"
                    document.last_verified_at = NOW

        if not dry_run:
            db.flush()
        print(f"1. SourceDocument updates: {source_updates}")

        applied = 0
        skipped = 0
        for citation in CITATIONS:
            qid, function_number, document_key, locator, excerpt = citation
            question = db.query(Question).filter_by(question_id=qid).first()
            if question is None:
                raise RuntimeError(f"Question not found: {qid}")
            scope = db.query(QuestionOpecScope).filter_by(
                question_id=qid,
                opec_profile_id=profile.id,
            ).first()
            if scope is None:
                raise RuntimeError(f"OPEC scope not found: {qid}")
            if scope.function_number != function_number:
                raise RuntimeError(
                    f"Function drift for {qid}: F{scope.function_number} != F{function_number}"
                )
            if scope.bank_partition != "training":
                raise RuntimeError(
                    f"Refusing to promote non-training question {qid} from {scope.bank_partition}."
                )

            if _already_correct(question, citation, db, profile.id):
                skipped += 1
                continue
            if dry_run:
                print(f"  [dry-run] Would verify F{function_number} {qid[:12]}")
                applied += 1
                continue

            for field, value in CONTENT_PATCHES.get(qid, {}).items():
                setattr(question, field, value)

            if audit_question_structure(question)["status"] != "PASS":
                raise RuntimeError(f"Structural audit failed after patch: {qid}")

            source_doc = _source_doc(db, document_key)
            if source_doc is None:
                raise RuntimeError(f"Source document not found: {document_key}")

            db.query(QuestionCitation).filter_by(question_id=qid).delete(
                synchronize_session=False
            )
            db.add(QuestionCitation(
                question_id=qid,
                source_document_id=source_doc.id,
                locator=locator,
                excerpt=excerpt,
                supports_key=True,
                verified_at=NOW,
                verified_by=ACTOR,
            ))

            report = dict(question.quality_report) if isinstance(question.quality_report, dict) else {}
            report["source_verification"] = {
                "status": "official_current",
                "url": source_doc.official_url,
                "locator": locator,
                "supporting_excerpt": excerpt,
                "verified_on": NOW.isoformat(),
                "verified_by": ACTOR,
            }
            report["review"] = "source_grounded"
            question.quality_report = report
            question.is_verified = True

            difficulty = editorial_question_difficulty(question)
            content_hash = question_revision_hash(question, difficulty)
            max_revision = db.query(func.max(QuestionRevision.revision_number)).filter_by(
                question_id=qid
            ).scalar() or 0
            db.add(QuestionRevision(
                question_id=qid,
                revision_number=max_revision + 1,
                content_hash=content_hash,
                stem=question.stem,
                options_json=question.options_json,
                correct_key=question.correct_key,
                rationale=question.rationale,
                bank_partition="training",
                source_snapshot={
                    "sources": [document_key],
                    "locator": locator,
                    "official_url": source_doc.official_url,
                },
                status="approved",
                change_reason="Canonical source review against current official text",
                actor=ACTOR,
                actor_type="system",
            ))
            applied += 1

        print(f"2. Questions: {applied} applied, {skipped} already correct")

        if dry_run:
            print("3. [dry-run] Delivery check skipped")
            return

        db.commit()

        from services.question_service import _canonical_deliverable_question_ids

        scopes = db.query(QuestionOpecScope).filter_by(opec_profile_id=profile.id).all()
        questions = db.query(Question).filter(
            Question.question_id.in_([scope.question_id for scope in scopes])
        ).all()
        partitions = {
            str(scope.question_id): scope.bank_partition
            for scope in scopes
        }
        deliverable = _canonical_deliverable_question_ids(
            db,
            questions,
            scope_partitions=partitions,
        )
        delivered = set(BATCH_QIDS) & deliverable
        print(f"3. Batch deliverable: {len(delivered)}/{len(BATCH_QIDS)}")
        print(f"4. Total canonical deliverable for OPEC 236769: {len(deliverable)}")
        if len(delivered) != len(BATCH_QIDS):
            missing = sorted(set(BATCH_QIDS) - delivered)
            raise RuntimeError(f"Canonical delivery failed for: {missing}")
        if set(EXCLUDED_REDUNDANT_QIDS) & deliverable:
            raise RuntimeError("A redundant excluded candidate became deliverable unexpectedly.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
