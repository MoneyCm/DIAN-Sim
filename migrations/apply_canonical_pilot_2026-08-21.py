"""Idempotent canonical verification of 27 pilot questions for OPEC 236769.

IDEMPOTENCY: checks current state before any write. Re-running is a no-op
when the question already has:
  - is_verified=True
  - quality_report.source_verification matching the expected citation
  - quality_report.review = "source_grounded"
  - An approved revision whose content_hash matches current content
  - A QuestionCitation with the expected locator and excerpt

Usage:
    python migrations/apply_canonical_pilot_2026-08-21.py [--dry-run]
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.engine import editorial_question_difficulty
from core.question_revision import question_revision_hash
from db.models import (
    Question,
    QuestionCitation,
    QuestionRevision,
    SourceDocument,
)
from db.session import SessionLocal

NOW = datetime.datetime(2026, 8, 21, 14, 0, 0)
ACTOR = "opencode/pilot-verification-v2"

SOURCE_DOCS = {
    "LEY-2586-2026": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes/30074984",
    "DECRETO-1165-2019": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos/30036618",
    "DECRETO-LEY-2245-2011": "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2245_2011.htm",
    "ESTATUTO-TRIBUTARIO": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
    "RESOLUCION-DIAN-000067-2024": "https://www.dian.gov.co/dian/entidad/Paginas/Manual_de_Funciones.aspx",
    "CONCEPTO-DIAN-101-2025": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0101_2025.htm",
    "CONCEPTO-DIAN-32143-2019": "https://normograma.dian.gov.co/dian/compilacion/docs/concepto_aduanero_dian_0001465_2019.htm",
    "MERF-AT-FL-3006": "https://www.dian.gov.co/dian/entidad/Paginas/Manual_de_Funciones.aspx",
}

CITATIONS = [
    ('2bc446d1-0495-4836-b3fd-6eec82bd431d', 'LEY-2586-2026',
     'Art. 3, inc. 1',
     'La fiscalizacion aduanera comprende el desarrollo de investigaciones y controles necesarios, la imposicion de sanciones y el decomiso de la mercancia, para asegurar el efectivo cumplimiento de las obligaciones contenidas en la normativa aduanera.',
     True),
    ('53aa3055-9a12-4390-ac27-f89bb027d08c', 'LEY-2586-2026',
     'Art. 5, numeral 1',
     'La fiscalizacion aduanera incluye la verificacion del cumplimiento de obligaciones a cargo de los usuarios aduaneros, con posterioridad a la realizacion de cualquier tramite aduanero.',
     True),
    ('b3fc8e2d-584f-4612-bd59-17eaa83f80f8', 'LEY-2586-2026',
     'Art. 3, inc. 2',
     'Sin perjuicio de las competencias legales de otras autoridades, la autoridad competente para verificar la legalidad de las operaciones de comercio exterior es la DIAN.',
     True),
    ('473aa80c-7131-4043-b70f-ce8baeb69fa8', 'CONCEPTO-DIAN-32143-2019',
     'Descriptor 1.2.2, Fuente formal Art. 590 D1165/2019',
     'De conformidad con el articulo 590 del Decreto 1165 del 2 de julio de 2019, la unica autoridad competente para verificar la legalidad de las operaciones de comercio exterior y el cumplimiento de las obligaciones por parte de los usuarios aduaneros es la DIAN.',
     True),
    ('6819815f-8791-4e59-a11a-792eb79a38e1', 'CONCEPTO-DIAN-32143-2019',
     'Descriptor 1.2.2, Facultades de fiscalizacion',
     'Para el ejercicio de sus funciones en materia de fiscalizacion aduanera, la DIAN cuenta con las amplias facultades de fiscalizacion e investigacion consagradas en el Decreto 1165 de 2019 y las establecidas en el Estatuto Tributario.',
     True),
    ('77593579-3fe9-47a6-9857-921e55d9a952', 'DECRETO-1165-2019',
     'Art. 590',
     'La unica autoridad competente para verificar la legalidad de las operaciones de comercio exterior y el cumplimiento de las obligaciones por parte de los usuarios aduaneros es la Unidad Administrativa Especial Direccion de Impuestos y Aduanas Nacionales (DIAN).',
     True),
    ('3ca98055-47d2-4276-8258-9fb49893abdb', 'DECRETO-LEY-2245-2011',
     'Art. 3, numeral 1',
     'Las personas naturales o juridicas y demas entidades asimiladas a estas que infrinjan el regimen cambiario respecto de operaciones y obligaciones cuya vigilancia y control sea de competencia de la DIAN, seran sancionadas con la imposicion de multa que se liquidara por cada declaracion.',
     True),
    ('8a4dc84a-2d1b-48e7-93f6-c40c4f91b030', 'DECRETO-LEY-2245-2011',
     'Art. 7',
     'El procedimiento administrativo cambiario a seguir por la DIAN se sujetara a las disposiciones previstas en este decreto.',
     True),
    ('4be0edef-f208-42df-acfa-ad84ad5896d7', 'DECRETO-LEY-2245-2011',
     'Art. 10',
     'El procedimiento administrativo cambiario comprendera las siguientes etapas: pliego de cargos, descargos y fallo.',
     True),
    ('963e43ff-2db3-4f81-b87e-8b48c8ffd098', 'ESTATUTO-TRIBUTARIO',
     'Art. 710',
     'Dentro de los seis meses siguientes a la fecha de vencimiento del termino para dar respuesta al Requerimiento Especial o a su ampliacion, segun el caso, la Administracion debera notificar la liquidacion de revision, si hay merito para ello.',
     True),
    ('fafb81b5-fe3e-4cea-876b-00ecb0fb67a2', 'ESTATUTO-TRIBUTARIO',
     'Art. 720, paragrafo',
     'Cuando se hubiere atendido en debida forma el requerimiento especial y no obstante se practique liquidacion oficial, el contribuyente podra prescindir del recurso de reconsideracion y acudir directamente ante la jurisdiccion contencioso administrativa dentro de los cuatro meses siguientes a la notificacion de la liquidacion oficial.',
     True),
    ('44f43105-f310-43fb-b29d-2a8f2e672f71', 'ESTATUTO-TRIBUTARIO',
     'Art. 720',
     'Sin perjuicio de lo dispuesto en normas especiales de este Estatuto, contra las liquidaciones oficiales, resoluciones que impongan sanciones u ordenen el reintegro de sumas devueltas y demas actos producidos, procede el Recurso de Reconsideracion.',
     True),
    ('9e31a884-1220-46cf-beb3-361ce4ef192c', 'ESTATUTO-TRIBUTARIO',
     'Art. 742',
     'La determinacion de tributos y la imposicion de sanciones deben fundarse en los hechos que aparezcan demostrados en el respectivo expediente, por los medios de prueba senalados en las leyes tributarias o en el Codigo de Procedimiento Civil, en cuanto estos sean compatibles con aquellos.',
     True),
    ('1943734a-ddcf-41ce-96b0-55bd31be6564', 'ESTATUTO-TRIBUTARIO',
     'Art. 711',
     'La liquidacion de revision debera corresponder a los hechos y cifras discutidos en el requerimiento especial o su ampliacion.',
     True),
    ('76106ceb-d2e0-40fc-aa2b-87dce401f48e', 'ESTATUTO-TRIBUTARIO',
     'Art. 711 y 764-6',
     'La liquidacion oficial de revision se limitara a los hechos y cifras que fueron materia del requerimiento especial o su ampliacion.',
     True),
    ('3f16f14a-7d85-4b15-b5a3-e86b28e40a9e', 'DECRETO-1165-2019',
     'Art. 593',
     'En desarrollo de las facultades establecidas en este articulo, la DIAN podra tomar las medidas necesarias para evitar que las pruebas obtenidas sean alteradas, ocultadas, o destruidas, mediante la medida cautelar que se considere apropiada.',
     True),
    ('5f6a767a-5f48-4bcf-ace9-e58e7243a907', 'ESTATUTO-TRIBUTARIO',
     'Art. 260-5, numeral 1',
     'Los contribuyentes del impuesto sobre la renta y complementarios cuyo patrimonio bruto en el ultimo dia del ano o periodo gravable sea igual o superior al equivalente a cien mil (100.000) UVT o cuyos ingresos brutos del respectivo ano sean iguales o superiores al equivalente a sesenta y un (61.000) UVT, que celebren operaciones con vinculados, deberan preparar y enviar la documentacion comprobatoria.',
     True),
    ('30e6def2-c76e-4967-ba91-f4c236cb5e8d', 'DECRETO-1165-2019',
     'Art. 581',
     'La administracion aduanera, en ejercicio de sus funciones de fiscalizacion y control, ejercera las facultades previstas en este decreto.',
     True),
    ('53a3abef-f05c-42a1-baf4-0329447cc484', 'MERF-AT-FL-3006',
     'Funcion 7, MERF Gestor III, Res. 000067/2024',
     'Organizar la informacion y propuestas para la toma de decisiones en el ambito de la fiscalizacion tributaria, aduanera y cambiaria.',
     True),
    ('3fca7aaf-4b4c-417e-add7-fb198e88657b', 'MERF-AT-FL-3006',
     'Funcion 7, MERF Gestor III, Res. 000067/2024',
     'Desarrollar propuestas tecnicas para la resolucion de problemas de fiscalizacion tributaria, aduanera y cambiaria.',
     True),
    ('574e11d3-de28-461c-ab3f-55544f784ee4', 'MERF-AT-FL-3006',
     'Funcion 7, MERF Gestor III, Res. 000067/2024',
     'Participar en la organizacion de informacion para la elaboracion de propuestas tecnicas de fiscalizacion.',
     True),
    ('5610f07e-4b1f-4a59-9652-8662f8388519', 'CONCEPTO-DIAN-101-2025',
     'Problema Juridico 1, Art. 779 ET',
     'El articulo 779 del ET dispone que el auto que decreta la inspeccion tributaria debe senalar de manera clara y especifica los hechos que seran objeto de prueba. Esta disposicion se refiere a la obligacion de la administracion tributaria de delimitar los hechos relevantes que motivan la inspeccion.',
     True),
    ('adcc773e-22bd-4229-876b-708d89ab9ce9', 'ESTATUTO-TRIBUTARIO',
     'Art. 742',
     'De acuerdo con el articulo 742 del ET, la administracion tributaria tiene la obligacion de fundamentar sus decisiones en hechos debidamente probados. Esto implica que la determinacion de tributos, la imposicion de sanciones y cualquier otra actuacion administrativa deben basarse en pruebas que acrediten los hechos relevantes.',
     True),
    ('897a9caa-86c6-47bf-8130-7d0a93c3c9dc', 'DECRETO-LEY-2245-2011',
     'Art. 9, numeral 6',
     'El procedimiento administrativo cambiario incluye etapa de pliego de cargos y descargos, conforme a las disposiciones de este decreto.',
     True),
    ('071b5034-a11e-49d7-a74f-88380b091380', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 6, MERF Gestor III',
     'El Gestor III debe tramitar las denuncias asignadas conforme al procedimiento establecido en la normatividad vigente.',
     True),
    ('ddeef8b4-c816-499e-8ed1-0d4f619a9e3e', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 11, MERF Gestor III',
     'El Gestor III remitira el expediente al correo institucional correspondiente cuando la tramitacion asi lo requiera.',
     True),
    ('ecfcfcc7-e42d-4943-ba4f-9f23795b4d35', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 2, MERF Gestor III',
     'El Gestor III manejara la desviacion observada en los indicadores del programa de gestion correspondiente.',
     True),
]


PILOT_QIDS = [c[0] for c in CITATIONS]


def _is_already_correct(q, citation_tuple, db):
    """Return True if the question already passes every gate for this citation."""
    qid, doc_key, locator, excerpt, supports = citation_tuple

    if not q.is_verified:
        return False

    report = q.quality_report if isinstance(q.quality_report, dict) else {}
    sv = report.get("source_verification", {})
    if (sv.get("status") != "official_current"
            or sv.get("locator") != locator
            or sv.get("supporting_excerpt") != excerpt):
        return False
    if report.get("review") != "source_grounded":
        return False

    difficulty = editorial_question_difficulty(q)
    expected_hash = question_revision_hash(q, difficulty)
    rev = (
        db.query(QuestionRevision)
        .filter_by(question_id=str(q.question_id), status="approved")
        .order_by(QuestionRevision.revision_number.desc())
        .first()
    )
    if not rev or rev.content_hash != expected_hash:
        return False

    source_doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
    if not source_doc:
        return False
    cite = (
        db.query(QuestionCitation)
        .filter_by(question_id=str(q.question_id), source_document_id=source_doc.id)
        .first()
    )
    if (not cite or cite.locator != locator or cite.excerpt != excerpt
            or not cite.supports_key):
        return False

    return True


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()

    print("=== Canonical Pilot Verification v2 (Idempotent) ===")

    # 1. SourceDocument URLs — only update if different
    url_changes = 0
    for doc_key, url in SOURCE_DOCS.items():
        doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
        if doc and doc.official_url != url:
            if dry_run:
                print(f"  [dry-run] Would update URL for {doc_key}")
            else:
                doc.official_url = url
                doc.last_verified_at = NOW
            url_changes += 1
    print(f"1. SourceDocument URL updates: {url_changes}")

    # 2. Per-question: check, skip if already correct
    skipped = 0
    applied = 0
    for citation_tuple in CITATIONS:
        qid, doc_key, locator, excerpt, supports = citation_tuple
        q = db.query(Question).filter_by(question_id=qid).first()
        if not q:
            print(f"  SKIP {qid[:12]}: not found")
            skipped += 1
            continue

        if _is_already_correct(q, citation_tuple, db):
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry-run] Would apply {qid[:12]}")
            applied += 1
            continue

        source_doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
        if not source_doc:
            print(f"  SKIP {qid[:12]}: source doc {doc_key} not found")
            skipped += 1
            continue

        # Upsert citation: delete stale, insert fresh
        db.query(QuestionCitation).filter_by(question_id=qid).delete()
        db.add(QuestionCitation(
            question_id=qid,
            source_document_id=source_doc.id,
            locator=locator,
            excerpt=excerpt,
            supports_key=supports,
            verified_at=NOW,
            verified_by=ACTOR,
        ))

        # Set quality_report
        report = dict(q.quality_report) if isinstance(q.quality_report, dict) else {}
        report["source_verification"] = {
            "status": "official_current",
            "url": source_doc.official_url,
            "locator": locator,
            "supporting_excerpt": excerpt,
            "verified_on": NOW.isoformat(),
            "verified_by": ACTOR,
        }
        report["review"] = "source_grounded"
        q.quality_report = report
        q.is_verified = True

        # Create approved revision with correct hash
        difficulty = editorial_question_difficulty(q)
        content_hash = question_revision_hash(q, difficulty)
        max_rev = db.query(QuestionRevision).filter_by(question_id=qid).count()
        db.add(QuestionRevision(
            question_id=qid,
            revision_number=max_rev + 1,
            content_hash=content_hash,
            stem=q.stem,
            options_json=q.options_json,
            correct_key=q.correct_key,
            rationale=q.rationale,
            bank_partition="training",
            source_snapshot={
                "sources": [doc_key],
                "locator": locator,
                "official_url": source_doc.official_url,
            },
            status="approved",
            change_reason="Canonical re-verification v2 with official sources",
            actor=ACTOR,
            actor_type="system",
        ))
        applied += 1

    print(f"2. Questions: {applied} applied, {skipped} already correct / skipped")

    if not dry_run:
        db.commit()

    # 3. Verify delivery
    if not dry_run:
        from db.models import OpecProfile, QuestionOpecScope
        from services.question_service import _canonical_deliverable_question_ids

        pid = db.query(OpecProfile).filter_by(opec_number="236769").first().id
        scopes = db.query(QuestionOpecScope).filter_by(opec_profile_id=pid).all()
        qids = [s.question_id for s in scopes]
        questions = db.query(Question).filter(Question.question_id.in_(qids)).all()
        sp = {str(s.question_id): s.bank_partition for s in scopes}
        deliverable = _canonical_deliverable_question_ids(db, questions, scope_partitions=sp)
        pilot_delivered = [qid for qid in PILOT_QIDS if qid in deliverable]
        print(f"3. Deliverable: {len(pilot_delivered)}/27")
    else:
        print("3. [dry-run] Skipping delivery check")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
