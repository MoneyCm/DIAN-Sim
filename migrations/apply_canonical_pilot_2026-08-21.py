"""Idempotent canonical verification of 27 pilot questions for OPEC 236769.

IDEMPOTENCY: checks current state before any write. Re-running is a no-op
when the question already has:
  - is_verified=True
  - quality_report.source_verification matching the expected citation
  - quality_report.review = "source_grounded"
  - The latest revision approved, in training, with a current content hash
  - A verified QuestionCitation with the expected locator and excerpt
  - The exact official source URL marked current
  - The OPEC 236769 scope in the training partition

Usage:
    python migrations/apply_canonical_pilot_2026-08-21.py [--dry-run]
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.engine import editorial_question_difficulty
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

NOW = datetime.datetime(2026, 8, 21, 18, 0, 0)
ACTOR = "codex/canonical-source-review-2026-08-21"

SOURCE_DOCS = {
    "LEY-2586-2026": "https://normograma.dian.gov.co/dian/compilacion/docs/ley_2586_2026.htm",
    "DECRETO-1165-2019": "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1165_2019.htm",
    "DECRETO-LEY-2245-2011": "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2245_2011.htm",
    "ESTATUTO-TRIBUTARIO": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
    "RESOLUCION-DIAN-000067-2024": "https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0067_2024.htm",
    "CONCEPTO-DIAN-101-2025": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0101_2025.htm",
    "CONCEPTO-DIAN-32143-2019": "https://normograma.dian.gov.co/dian/compilacion/docs/concepto_aduanero_dian_0001465_2019.htm",
    "MERF-AT-FL-3006": "https://www.dian.gov.co/dian/entidad/ManualFunciones1/FTGH_1824_Gestor_III_AT_FL_3006.PDF",
    "PR-COA-0501": "https://www.dian.gov.co/atencionciudadano/LMDP/Cumplimiento-Obligaciones-Aduaneras-y-Cambiarias/Fiscalizacion-y-Liquidacion/Procedimientos/PR-COA-0501.pdf",
    "OD-COA-0106": "https://www.dian.gov.co/atencionciudadano/LMDP/Cumplimiento-Obligaciones-Aduaneras-y-Cambiarias/Fiscalizacion-y-Liquidacion/Otros-documentos/OD-COA-0106.pdf",
}

SOURCE_DOC_METADATA = {
    "PR-COA-0501": {
        "title": "Auditoria posterior al despacho",
        "document_type": "procedimiento",
        "version": "1",
        "valid_from": datetime.date(2024, 10, 21),
    },
    "OD-COA-0106": {
        "title": "Guia de implementacion de auditoria posterior al despacho - APD en Colombia",
        "document_type": "guia",
        "version": "1",
        "valid_from": datetime.date(2024, 12, 19),
    },
}

CITATIONS = [
    ('2bc446d1-0495-4836-b3fd-6eec82bd431d', 'LEY-2586-2026',
     'Art. 3, paragrafo, numeral 3',
     'Por falta de competencia de la DIAN, caso en el cual debera remitirse a la Entidad competente.',
     True),
    ('53aa3055-9a12-4390-ac27-f89bb027d08c', 'LEY-2586-2026',
     'Art. 5, incisos 2 y 5',
     'La no respuesta a esta invitacion persuasiva no ocasiona sancion alguna. Cuando no se corrija o no se allane, se iniciara el procedimiento correspondiente.',
     True),
    ('b3fc8e2d-584f-4612-bd59-17eaa83f80f8', 'LEY-2586-2026',
     'Art. 3, paragrafo, numeral 6 e inciso final',
     'Cuando la conducta se califica como un error formal no sancionable, la decision de no iniciar la investigacion debera quedar soportada en un acta.',
     True),
    ('473aa80c-7131-4043-b70f-ce8baeb69fa8', 'CONCEPTO-DIAN-32143-2019',
     'Seccion 3.1, respuesta sobre combustible oculto y situacion del conductor',
     'La autoridad aduanera debe interponer la correspondiente denuncia ante la autoridad competente para que se determine la responsabilidad del conductor.',
     True),
    ('6819815f-8791-4e59-a11a-792eb79a38e1', 'CONCEPTO-DIAN-32143-2019',
     'Seccion 3.1, numeral 37 del articulo 647 D1165/2019',
     'El ocultamiento y una cantidad superior a veinte galones permiten adecuar la conducta al delito de contrabando de hidrocarburos y sus derivados.',
     True),
    ('77593579-3fe9-47a6-9857-921e55d9a952', 'CONCEPTO-DIAN-32143-2019',
     'Seccion 3.1, respuesta sobre combustible oculto y situacion del conductor',
     'La DIAN no tiene competencia para pronunciarse sobre la responsabilidad del conductor por el delito de contrabando de hidrocarburos.',
     True),
    ('3ca98055-47d2-4276-8258-9fb49893abdb', 'DECRETO-LEY-2245-2011',
     'Art. 3, numeral 1',
     'El numeral sanciona no presentar oportunamente la declaracion de cambio, presentarla con datos equivocados, no exhibirla o conservarla con sus soportes y no transmitirla al Banco de la Republica.',
     True),
    ('8a4dc84a-2d1b-48e7-93f6-c40c4f91b030', 'DECRETO-LEY-2245-2011',
     'Art. 7',
     'La actuacion podra iniciarse por informes de terceros o por cualquier medio que ofrezca credibilidad y para su desarrollo no se requerira el conocimiento del presunto infractor.',
     True),
    ('4be0edef-f208-42df-acfa-ad84ad5896d7', 'DECRETO-LEY-2245-2011',
     'Art. 10, inciso 2',
     'Si en una investigacion cambiaria se detectan posibles infracciones tributarias o aduaneras, se enviara copia de los documentos a la dependencia competente.',
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
     'Arts. 720, incisos 1 y 2, y 566-1, inciso 3',
     'Contra las liquidaciones oficiales procede el recurso de reconsideracion dentro de los dos meses siguientes a la notificacion; si esta fue electronica, el termino para impugnar comienza transcurridos cinco dias desde la entrega del correo.',
     True),
    ('9e31a884-1220-46cf-beb3-361ce4ef192c', 'ESTATUTO-TRIBUTARIO',
     'Art. 742',
     'La determinacion de tributos y la imposicion de sanciones deben fundarse en los hechos que aparezcan demostrados en el respectivo expediente, por los medios de prueba senalados en las leyes tributarias o en el Codigo de Procedimiento Civil, en cuanto estos sean compatibles con aquellos.',
     True),
    ('1943734a-ddcf-41ce-96b0-55bd31be6564', 'ESTATUTO-TRIBUTARIO',
     'Art. 712, literales b a h',
     'La liquidacion de revision debe contener periodo gravable, identificacion del contribuyente, bases, montos, explicacion sumaria de las modificaciones y firma o sello.',
     True),
    ('76106ceb-d2e0-40fc-aa2b-87dce401f48e', 'ESTATUTO-TRIBUTARIO',
     'Art. 711',
     'La liquidacion de revision debera contraerse exclusivamente a la declaracion y a los hechos contemplados en el requerimiento especial o en su ampliacion.',
     True),
    ('3f16f14a-7d85-4b15-b5a3-e86b28e40a9e', 'LEY-2586-2026',
     'Art. 5, inciso 1',
     'La DIAN podra invitar al usuario para que, dentro del mes siguiente a la comunicacion, presente la declaracion, pague o se allane con los beneficios aplicables.',
     True),
    ('5f6a767a-5f48-4bcf-ace9-e58e7243a907', 'ESTATUTO-TRIBUTARIO',
     'Art. 260-5, numeral 1',
     'Los contribuyentes que superen los topes y celebren operaciones con vinculados deberan preparar y enviar un informe maestro y un informe local relativo a cada tipo de operacion.',
     True),
    ('30e6def2-c76e-4967-ba91-f4c236cb5e8d', 'DECRETO-1165-2019',
     'Arts. 578, numeral 3, y 581',
     'El control posterior se ejerce despues de la nacionalizacion y comprueba documentos comerciales y la exactitud de los datos consignados en las declaraciones aduaneras.',
     True),
    ('53a3abef-f05c-42a1-baf4-0329447cc484', 'PR-COA-0501',
     'Actividad 6, pagina 9',
     'Cuando el Plan de Trabajo Anual es rechazado, se devuelve a la actividad 4 para elaborar nuevamente el informe de presentacion de la propuesta.',
     True),
    ('3fca7aaf-4b4c-417e-add7-fb198e88657b', 'OD-COA-0106',
     'Numerales 1.4 y 1.6.1.2, paginas 17 y 19',
     'La seleccion objetiva considera sectores sensibles, analisis de riesgos, tipo de obligado y volumen de operaciones, entre otros factores.',
     True),
    ('574e11d3-de28-461c-ab3f-55544f784ee4', 'PR-COA-0501',
     'Actividad 7, pagina 9',
     'Se debe propender por la confidencialidad de los seleccionados en todas las etapas de seleccion, ejecucion y evaluacion de la Auditoria Posterior al Despacho.',
     True),
    ('5610f07e-4b1f-4a59-9652-8662f8388519', 'CONCEPTO-DIAN-101-2025',
     'Problema Juridico 1, Art. 779 ET',
     'El articulo 779 del ET dispone que el auto que decreta la inspeccion tributaria debe senalar de manera clara y especifica los hechos que seran objeto de prueba. Esta disposicion se refiere a la obligacion de la administracion tributaria de delimitar los hechos relevantes que motivan la inspeccion.',
     True),
    ('adcc773e-22bd-4229-876b-708d89ab9ce9', 'CONCEPTO-DIAN-101-2025',
     'Fundamentacion, numeral 4, Art. 742 ET',
     'De acuerdo con el articulo 742 del ET, la administracion tributaria tiene la obligacion de fundamentar sus decisiones en hechos debidamente probados. Esto implica que la determinacion de tributos, la imposicion de sanciones y cualquier otra actuacion administrativa deben basarse en pruebas que acrediten los hechos relevantes.',
     True),
    ('897a9caa-86c6-47bf-8130-7d0a93c3c9dc', 'DECRETO-LEY-2245-2011',
     'Art. 9, numeral 6',
     'La DIAN retendra los valores puestos a disposicion por otras autoridades y constituira los comprobantes de deposito o los entregara en custodia a la entidad bancaria correspondiente.',
     True),
    ('071b5034-a11e-49d7-a74f-88380b091380', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 6',
     'Atender las peticiones, quejas, sugerencias, reclamos y denuncias asignadas, de acuerdo con el proceso de desempeno y la normativa y procedimientos vigentes.',
     True),
    ('ddeef8b4-c816-499e-8ed1-0d4f619a9e3e', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 11',
     'Aplicar los lineamientos sobre seguridad de la informacion y proteccion de datos personales establecidos por la Entidad.',
     True),
    ('ecfcfcc7-e42d-4943-ba4f-9f23795b4d35', 'RESOLUCION-DIAN-000067-2024',
     'Art. 6, numeral 2',
     'Adelantar las acciones requeridas en la formulacion, seguimiento, evaluacion y ajuste de planes, programas o proyectos, incluyendo sus indicadores de gestion.',
     True),
]


PILOT_QIDS = [c[0] for c in CITATIONS]

QUESTION_CONTENT_PATCHES = {
    "3f16f14a-7d85-4b15-b5a3-e86b28e40a9e": {
        "option_key": "C",
        "option_text": (
            "Invitar al usuario mediante gestion persuasiva para que actue "
            "dentro del mes siguiente en los terminos legales."
        ),
        "rationale": (
            "Ante indicios de inexactitud o de una infraccion con sancion "
            "monetaria, el articulo 5 de la Ley 2586 de 2026 permite invitar "
            "al usuario mediante gestion persuasiva por el termino alli senalado."
        ),
        "source_refs": (
            "Ley 2586 de 2026, articulo 5 (Compilacion Juridica DIAN)."
        ),
    },
}


def _is_already_correct(q, citation_tuple, db, profile_id):
    """Return True if the question already passes every gate for this citation."""
    qid, doc_key, locator, excerpt, supports = citation_tuple

    if not q.is_verified:
        return False

    content_patch = QUESTION_CONTENT_PATCHES.get(qid)
    if content_patch:
        options = q.options_json if isinstance(q.options_json, dict) else {}
        if options.get(content_patch["option_key"]) != content_patch["option_text"]:
            return False
        if q.rationale != content_patch["rationale"]:
            return False
        if q.source_refs != content_patch["source_refs"]:
            return False

    report = q.quality_report if isinstance(q.quality_report, dict) else {}
    sv = report.get("source_verification", {})
    if (sv.get("status") != "official_current"
            or sv.get("url") != SOURCE_DOCS[doc_key]
            or sv.get("locator") != locator
            or sv.get("supporting_excerpt") != excerpt
            or not sv.get("verified_on")
            or not sv.get("verified_by")):
        return False
    if report.get("review") != "source_grounded":
        return False

    difficulty = editorial_question_difficulty(q)
    expected_hash = question_revision_hash(q, difficulty)
    rev = (
        db.query(QuestionRevision)
        .filter_by(question_id=str(q.question_id))
        .order_by(QuestionRevision.revision_number.desc())
        .first()
    )
    if (not rev or rev.status != "approved" or rev.bank_partition != "training"
            or rev.content_hash != expected_hash):
        return False

    source_doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
    if (not source_doc or source_doc.official_url != SOURCE_DOCS[doc_key]
            or source_doc.validity_status != "current"):
        return False
    cite = (
        db.query(QuestionCitation)
        .filter_by(question_id=str(q.question_id), source_document_id=source_doc.id)
        .first()
    )
    if (not cite or cite.locator != locator or cite.excerpt != excerpt
            or not cite.supports_key or not cite.verified_at
            or not str(cite.verified_by or "").strip()):
        return False

    scope = db.query(QuestionOpecScope).filter_by(
        question_id=str(q.question_id),
        opec_profile_id=profile_id,
    ).first()
    if not scope or scope.bank_partition != "training":
        return False

    return True


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    profile = db.query(OpecProfile).filter_by(opec_number="236769").first()
    if profile is None:
        raise RuntimeError("No existe el perfil OPEC 236769.")

    print("=== Canonical Pilot Verification v2 (Idempotent) ===")

    # 1. SourceDocument catalog — create missing documents and update stale URLs.
    url_changes = 0
    for doc_key, url in SOURCE_DOCS.items():
        doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
        if doc is None:
            if dry_run:
                print(f"  [dry-run] Would create source document {doc_key}")
            else:
                metadata = SOURCE_DOC_METADATA.get(doc_key, {})
                db.add(SourceDocument(
                    document_key=doc_key,
                    title=metadata.get("title", doc_key),
                    entity="DIAN",
                    document_type=metadata.get("document_type", "norma"),
                    official_url=url,
                    version=metadata.get("version"),
                    valid_from=metadata.get("valid_from"),
                    validity_status="current",
                    last_verified_at=NOW,
                ))
            url_changes += 1
        elif doc.official_url != url or doc.validity_status != "current":
            if dry_run:
                print(f"  [dry-run] Would update source document {doc_key}")
            else:
                doc.official_url = url
                doc.validity_status = "current"
                doc.last_verified_at = NOW
            url_changes += 1
    if not dry_run:
        # SessionLocal disables autoflush; make newly created source documents
        # queryable before processing their citations in the same transaction.
        db.flush()
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

        if _is_already_correct(q, citation_tuple, db, profile.id):
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry-run] Would apply {qid[:12]}")
            applied += 1
            continue

        scope = db.query(QuestionOpecScope).filter_by(
            question_id=qid,
            opec_profile_id=profile.id,
        ).first()
        if scope is None:
            print(f"  SKIP {qid[:12]}: canonical OPEC scope not found")
            skipped += 1
            continue

        source_doc = db.query(SourceDocument).filter_by(document_key=doc_key).first()
        if not source_doc:
            print(f"  SKIP {qid[:12]}: source doc {doc_key} not found")
            skipped += 1
            continue

        content_patch = QUESTION_CONTENT_PATCHES.get(qid)
        if content_patch:
            options = dict(q.options_json) if isinstance(q.options_json, dict) else {}
            options[content_patch["option_key"]] = content_patch["option_text"]
            q.options_json = options
            q.rationale = content_patch["rationale"]
            q.source_refs = content_patch["source_refs"]

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

        scope.bank_partition = "training"

        # Create approved revision with correct hash
        difficulty = editorial_question_difficulty(q)
        content_hash = question_revision_hash(q, difficulty)
        max_rev = db.query(func.max(QuestionRevision.revision_number)).filter_by(
            question_id=qid,
        ).scalar() or 0
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
            change_reason="Canonical source review with exact official support",
            actor=ACTOR,
            actor_type="system",
        ))
        applied += 1

    print(f"2. Questions: {applied} applied, {skipped} already correct / skipped")

    if not dry_run:
        db.commit()

    # 3. Verify delivery
    if not dry_run:
        from services.question_service import _canonical_deliverable_question_ids

        scopes = db.query(QuestionOpecScope).filter_by(
            opec_profile_id=profile.id,
        ).all()
        qids = [s.question_id for s in scopes]
        questions = db.query(Question).filter(Question.question_id.in_(qids)).all()
        sp = {str(s.question_id): s.bank_partition for s in scopes}
        deliverable = _canonical_deliverable_question_ids(db, questions, scope_partitions=sp)
        pilot_delivered = [qid for qid in PILOT_QIDS if qid in deliverable]
        print(f"3. Deliverable: {len(pilot_delivered)}/27")
        if len(pilot_delivered) != len(PILOT_QIDS):
            raise RuntimeError(
                "Canonical delivery verification failed: "
                f"{len(pilot_delivered)}/{len(PILOT_QIDS)} pilot questions."
            )
    else:
        print("3. [dry-run] Skipping delivery check")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
