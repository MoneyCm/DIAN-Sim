import os
import sys
import uuid
import json
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from db.models import CaseStudy, Question
from db.session import SessionLocal

# 4 Casos Protagónicos de Alta Complejidad para la OPEC 236769
NEW_CASES_DATA = [
    {
        "id": "case-06-devoluciones-iva",
        "title": "Caso 6: Fiscalización de Solicitudes de Devolución de Saldos a Favor en IVA e Inconsistencias en Facturación Electrónica",
        "text": "La sociedad 'Exportaciones Andinas Ltda.' presenta ante la División de Gestión de Devoluciones y Compensaciones de la Seccional de Impuestos de Bogotá una solicitud de devolución de saldo a favor en IVA por valor de COP 780 millones, originado por operaciones exentas con derecho a devolución bimestral. En la auditoría preventiva, el funcionario investigador de la DIAN cruza el reporte de facturación electrónica de compras y detecta que más del 40% de los costos soportados en el IVA descontable provienen de tres proveedores que presentan un estado de 'Inactivos' en el RUT, y cuyas facturas fueron emitidas bajo contingencias tecnológicas sospechosas sin validación previa. Ante la posible existencia de saldos a favor improcedentes, el funcionario decide suspender términos e iniciar una investigación formal.",
        "topic": "OPEC 236769 - Devoluciones Improcedentes e IVA Descontable",
        "difficulty": 3,
        "questions": [
            {
                "track": "FUNCIONAL",
                "competency": "Procedimiento Tributario",
                "topic": "OPEC 236769 - Auto de Suspensión de Términos",
                "macro_dominio": "Tributario",
                "micro_competencia": "Actos Administrativos",
                "difficulty": 3,
                "stem": "SITUACIÓN: Ante las serias inconsistencias en las facturas electrónicas de 'Exportaciones Andinas Ltda.', el auditor de la DIAN proyecta suspender el término para la devolución. PREGUNTA: De acuerdo con el Artículo 857-1 del Estatuto Tributario, ¿cuál es el plazo máximo por el cual la DIAN puede suspender los términos del trámite de devolución para adelantar la investigación correspondiente?",
                "options": {
                    "A": "Hasta por un término máximo de noventa (90) días calendario.",
                    "B": "Hasta por un término máximo de noventa (90) días hábiles.",
                    "C": "Hasta por un término máximo de sesenta (60) días calendario."
                },
                "correct_key": "A",
                "rationale": "El Artículo 857-1 del Estatuto Tributario estipula expresamente que el término para devolver o compensar podrá suspenderse hasta por un término máximo de noventa (90) días calendario, a fin de que la División de Fiscalización adelante la investigación correspondiente ante indicios de improcedencia."
            },
            {
                "track": "FUNCIONAL",
                "competency": "Régimen Sancionatorio",
                "topic": "OPEC 236769 - Sanción Devolución Improcedente",
                "macro_dominio": "Tributario",
                "micro_competencia": "Sanciones Tributarias",
                "difficulty": 3,
                "stem": "SITUACIÓN: Si la DIAN rechaza la devolución y comprueba que se utilizaron facturas apócrifas para reclamar indebidamente el saldo a favor en IVA. PREGUNTA: Conforme al Artículo 670 del Estatuto Tributario, ¿cuál es la sanción aplicable en caso de devoluciones o compensaciones que resulten improcedentes cuando se utilicen documentos falsos o fraude?",
                "options": {
                    "A": "Sanción equivalente al cien por ciento (100%) del valor devuelto en forma improcedente, más intereses moratorios.",
                    "B": "Sanción equivalente al doscientos por ciento (200%) del valor devuelto en forma improcedente, más intereses moratorios.",
                    "C": "Sanción del cincuenta por ciento (50%) de los ingresos brutos del período fiscal del contribuyente."
                },
                "correct_key": "B",
                "rationale": "El Artículo 670 del E.T. determina que cuando la solicitud de devolución o compensación resulte improcedente por haberse utilizado documentos falsos o fraude, la sanción será del doscientos por ciento (200%) del valor devuelto en forma improcedente."
            },
            {
                "track": "FUNCIONAL",
                "competency": "Detección de Evasión",
                "topic": "OPEC 236769 - Requisitos Factura Electrónica",
                "macro_dominio": "Tributario",
                "micro_competencia": "Obligaciones Formales",
                "difficulty": 3,
                "stem": "SITUACIÓN: Al analizar las facturas de 'Exportaciones Andinas Ltda.', el funcionario nota que varias compras no están registradas en el Registro de Facturas Electrónicas de la DIAN (MUISCA). PREGUNTA: Conforme al Artículo 616-1 del Estatuto Tributario, ¿cuál es el efecto de utilizar soportes que no cuenten con validación previa de la DIAN para la aceptación de costos y deducciones?",
                "options": {
                    "A": "No constituirán costo, deducción ni impuesto descontable en el impuesto sobre la renta e IVA.",
                    "B": "Serán aceptados con una penalización del diez por ciento (10%) del valor total de la transacción.",
                    "C": "Darán lugar a la suspensión inmediata del RUT del adquirente pero serán fiscalmente procedentes."
                },
                "correct_key": "A",
                "rationale": "De acuerdo con el Artículo 616-1 del E.T., para la procedencia de costos, deducciones e impuestos descontables, las facturas de venta y documentos equivalentes deben contar con la validación previa de la DIAN antes de su expedición."
            }
        ]
    },
    {
        "id": "case-07-precios-transferencia",
        "title": "Caso 7: Fiscalización de Operaciones Vinculadas, Precios de Transferencia y Planificación Fiscal Agresiva",
        "text": "La multinacional 'Farmacéutica Global Colombia S.A.' realiza compras millonarias de principios activos e intangibles (marcas y patentes) a su matriz vinculada ubicada en Suiza, y a su filial logística en Delaware (EE. UU.), esta última considerada una jurisdicción de baja imposición tributaria. El auditor del área de Fiscalización Internacional de la DIAN detecta que la sucursal en Colombia reporta pérdidas fiscales recurrentes desde hace tres años, mientras que sus vinculadas en el extranjero registran márgenes de rentabilidad del 45%. El gestor a cargo debe evaluar el cumplimiento de las obligaciones del régimen de precios de transferencia y la deducibilidad de las regalías pagadas.",
        "topic": "OPEC 236769 - Fiscalización Internacional y Precios de Transferencia",
        "difficulty": 3,
        "questions": [
            {
                "track": "FUNCIONAL",
                "competency": "Investigación Tributaria",
                "topic": "OPEC 236769 - Principio de Plena Competencia",
                "macro_dominio": "Tributario",
                "micro_competencia": "Fiscalización Internacional",
                "difficulty": 3,
                "stem": "SITUACIÓN: El auditor de la DIAN debe comprobar si los precios de adquisición pactados con Delaware se ajustaron al mercado general. PREGUNTA: ¿Cómo se denomina el principio rector internacional incorporado en el Artículo 260-1 del E.T. según el cual las operaciones entre vinculadas deben pactarse con los mismos márgenes de los terceros independientes?",
                "options": {
                    "A": "Principio de Plena Competencia (Arm's Length Principle).",
                    "B": "Principio de Favorabilidad Comercial Transnacional.",
                    "C": "Principio de Autonomía Cambiaria y Tributaria."
                },
                "correct_key": "A",
                "rationale": "El Artículo 260-1 del Estatuto Tributario colombiano estipula el Principio de Plena Competencia (Arm's Length), que obliga a los contribuyentes del impuesto sobre la renta que realicen operaciones con vinculados del exterior a determinar sus ingresos ordinarios y extraordinarios, costos y deducciones considerando los precios y márgenes de operaciones comparables realizadas entre partes independientes."
            },
            {
                "track": "FUNCIONAL",
                "competency": "Detección de Evasión",
                "topic": "OPEC 236769 - Limitación de Gastos en Paraísos",
                "macro_dominio": "Tributario",
                "micro_competencia": "Evasión y Elusión",
                "difficulty": 3,
                "stem": "SITUACIÓN: 'Farmacéutica Global Colombia S.A.' deduce pagos a Delaware sin demostrar que la vinculada desarrolló actividades reales. PREGUNTA: De acuerdo con el Artículo 124-2 del Estatuto Tributario, ¿cuál es el requisito obligatorio para deducir costos o gastos pagados a personas o entidades constituidas en jurisdicciones no cooperantes o de baja imposición (paraísos fiscales) ante la DIAN?",
                "options": {
                    "A": "Demostrar que la operación es real y que se pactó a precios de mercado, además de haber practicado la retención en la fuente si corresponde.",
                    "B": "Contar con el visto bueno del cónsul de Colombia en el país de destino y registrar la factura en la Cámara de Comercio.",
                    "C": "No existe ningún requisito especial siempre que la factura se haya emitido electrónicamente en el extranjero."
                },
                "correct_key": "A",
                "rationale": "El Artículo 124-2 del E.T. exige que para la procedencia de costos y deducciones de operaciones con paraísos fiscales se debe probar que la transacción es real y se efectuó por valores comerciales de mercado, además de la debida práctica de retenciones."
            }
        ]
    },
    {
        "id": "case-08-control-cambiario",
        "title": "Caso 8: Fiscalización Aduanera, Control Cambiario y Detección de Operaciones Sospechosas por Subfacturación",
        "text": "La importadora 'Zapatos Premium S.A.' nacionaliza en la Seccional de Aduanas de Cartagena un cargamento de calzado deportivo de alta gama proveniente de Asia, declarando un valor FOB de USD 2 por unidad. Un inspector de fiscalización aduanera de la DIAN sospecha de una subfacturación masiva del 90% en comparación con los valores de referencia del sistema aduanero. Al cruzar la información cambiaria del Banco de la República, se encuentra que la empresa giró divisas por el canal oficial por un valor total de USD 450.000, pero la Declaración de Importación (Formulario 500) solo ampara USD 45.000. El gestor debe detectar la infracción aduanera y el canal ilegal de divisas.",
        "topic": "OPEC 236769 - Fiscalización Aduanera y Cambiaria",
        "difficulty": 3,
        "questions": [
            {
                "track": "FUNCIONAL",
                "competency": "Fiscalización Aduanera",
                "topic": "OPEC 236769 - Valoración Aduanera y Duda",
                "macro_dominio": "Aduanero",
                "micro_competencia": "Procedimiento Aduanero",
                "difficulty": 3,
                "stem": "SITUACIÓN: El funcionario de la DIAN duda del valor declarado FOB de USD 2. PREGUNTA: De acuerdo con el Acuerdo de Valoración de la OMC y la normativa aduanera de la DIAN, ¿cómo se denomina el acto procesal con el cual la administración rechaza provisionalmente el precio declarado y exige garantías al importador ante precios irrisorios?",
                "options": {
                    "A": "Duda Razonable en Valoración Aduanera.",
                    "B": "Liquidación Provisional de Aforo Aduanero.",
                    "C": "Auto de Inadmisión de la Declaración de Aduana."
                },
                "correct_key": "A",
                "rationale": "La Duda Razonable es el mecanismo mediante el cual la DIAN, amparada en las directrices de la OMC, notifica al importador que el valor declarado presenta discrepancias graves con los precios de referencia del mercado y le solicita justificación técnica o constitución de garantías."
            },
            {
                "track": "FUNCIONAL",
                "competency": "Investigación Tributaria",
                "topic": "OPEC 236769 - Infracción Cambiaria",
                "macro_dominio": "Aduanero",
                "micro_competencia": "Régimen Cambiario",
                "difficulty": 3,
                "stem": "SITUACIÓN: La DIAN comprueba que la empresa canalizó divisas por USD 405.000 adicionales que no guardan correspondencia con el valor aduanero declarado. PREGUNTA: ¿Bajo qué cargo formula la Subdirección de Fiscalización Cambiaria de la DIAN la sanción correspondiente por la no correspondencia de canalización de divisas según el Decreto Ley 2245 de 2011?",
                "options": {
                    "A": "Infracción cambiaria por canalizar divisas por valores que no corresponden a la operación de importación real.",
                    "B": "Infracción cambiaria por no declarar divisas en efectivo en la aduana de ingreso físico.",
                    "C": "Delito de captación masiva e ilegal de recursos del público en el exterior."
                },
                "correct_key": "A",
                "rationale": "El régimen sancionatorio de cambios administrado por la DIAN castiga con severidad la alteración o no correspondencia de los valores girados frente a los valores aduaneros nacionalizados, tipificando esto como una infracción cambiaria de control de flujos de divisas."
            }
        ]
    },
    {
        "id": "case-09-regimen-simple",
        "title": "Caso 9: Sanción por Abuso, Simulación Laboral y Exclusión del Régimen Simple de Tributación (RST)",
        "text": "La firma 'Consultores Asociados del Norte S.A.S.' despidió a sus diez analistas tributarios y los obligó a constituir empresas unipersonales independientes inscritas en el Régimen Simple de Tributación (RST). Posteriormente, firmó contratos de prestación de servicios con cada uno de ellos para que continuaran prestando las mismas labores en las oficinas de la firma, con el mismo horario y subordinación directa, pero liquidando sus impuestos bajo las tarifas preferenciales del RST en lugar de la retención en la fuente por salarios correspondientes. El gestor de la DIAN debe anular el beneficio del RST y reconfigurar la relación.",
        "topic": "OPEC 236769 - Régimen Simple de Tributación y Abuso",
        "difficulty": 3,
        "questions": [
            {
                "track": "FUNCIONAL",
                "competency": "Detección de Evasión",
                "topic": "OPEC 236769 - Exclusión del Régimen Simple",
                "macro_dominio": "Tributario",
                "micro_competencia": "Evasión y Elusión",
                "difficulty": 3,
                "stem": "SITUACIÓN: El gestor de la DIAN identifica que las empresas unipersonales constituidas por los analistas configuran una simulación laboral. PREGUNTA: De conformidad con el Artículo 906 del Estatuto Tributario, ¿qué personas naturales o jurídicas NO pueden optar por el Régimen Simple de Tributación (RST)?",
                "options": {
                    "A": "Las personas naturales que mantengan una relación laboral, laboral contratada o de subordinación con el contratante.",
                    "B": "Las personas naturales que presten servicios profesionales independientes sin subordinación.",
                    "C": "Las sociedades comerciales cuyos socios sean todos residentes en Colombia."
                },
                "correct_key": "A",
                "rationale": "El Artículo 906 del Estatuto Tributario prohíbe de forma taxativa la inscripción en el RST de personas naturales que mantengan una relación laboral o de subordinación directa, con el propósito de evitar la elusión del régimen salarial de retención y aportes."
            },
            {
                "track": "FUNCIONAL",
                "competency": "Procedimiento Tributario",
                "topic": "OPEC 236769 - Cláusula Antiabuso RST",
                "macro_dominio": "Tributario",
                "micro_competencia": "Actos Administrativos",
                "difficulty": 3,
                "stem": "SITUACIÓN: El auditor de la DIAN desestima las empresas del RST y reliquida la renta de 'Consultores Asociados del Norte S.A.S.' imputando las retenciones omitidas. PREGUNTA: De acuerdo con la Cláusula General Antiabuso (Artículo 869 del E.T.), ¿qué acción formal adelanta la DIAN para desconocer la simulación societaria y sancionar a la firma contratante?",
                "options": {
                    "A": "Reconfigurar la transacción de prestación de servicios a relación salarial directa y proferir Requerimiento Especial sancionando por no practicar retenciones.",
                    "B": "Denunciar a la empresa ante el Ministerio de Trabajo sin aplicar sanciones de naturaleza tributaria.",
                    "C": "Suspender temporalmente la personería jurídica de la constructora asociada ante la Superintendencia."
                },
                "correct_key": "A",
                "rationale": "La Cláusula General Antiabuso del E.T. permite a la DIAN desconocer la apariencia de los contratos independientes de prestación de servicios, desentrañar la realidad de la relación salarial y liquidar oficialmente las retenciones en la fuente omitidas más la sanción por inexactitud correspondiente."
            }
        ]
    }
]

def insert_new_cases():
    print("🚀 INICIANDO INSERCIÓN DE 4 NUEVOS CASOS PREMIUM Y 9 PREGUNTAS SITUACIONALES PARA OPEC 236769...")
    db = SessionLocal()
    try:
        from db.models import CaseStudy, Question
        from core.dedupe import compute_hash
        
        # Conectarse y verificar casos
        for case_data in NEW_CASES_DATA:
            # 1. Crear CaseStudy
            case_id = case_data["id"]
            title = case_data["title"]
            text_content = case_data["text"]
            topic = case_data["topic"]
            diff = case_data["difficulty"]
            
            # Verificar si ya existe
            existing_case = db.query(CaseStudy).filter_by(id=case_id).first()
            if existing_case:
                print(f"🔄 Caso '{title[:50]}' ya existe. Actualizando...")
                existing_case.title = title
                existing_case.text = text_content
                existing_case.topic = topic
                existing_case.difficulty = diff
                case_id = existing_case.id
            else:
                print(f"✨ Creando Caso: '{title[:50]}'")
                new_case = CaseStudy(
                    id=case_id,
                    title=title,
                    text=text_content,
                    topic=topic,
                    difficulty=diff
                )
                db.add(new_case)
                db.flush()
                
            # 2. Crear preguntas
            for q_data in case_data["questions"]:
                q_id = str(uuid.uuid4())
                stem = q_data["stem"]
                options = q_data["options"]
                correct_key = q_data["correct_key"]
                rat = q_data["rationale"]
                track = q_data["track"]
                comp = q_data["competency"]
                q_topic = q_data["topic"]
                macro = q_data["macro_dominio"]
                micro = q_data["micro_competencia"]
                q_diff = q_data["difficulty"]
                
                # Calcular hash único normativo para evitar colisiones
                raw_norm = f"{stem} | {correct_key}"
                import hashlib
                h_norm = hashlib.md5(raw_norm.encode('utf-8')).hexdigest()
                
                # Verificar si ya existe pregunta similar por hash_norm
                existing_q = db.query(Question).filter_by(hash_norm=h_norm).first()
                if existing_q:
                    print(f"   🔄 Pregunta ya existe. Omitiendo duplicado.")
                    continue
                    
                print(f"   ➕ Agregando pregunta: '{q_topic}'")
                new_q = Question(
                    question_id=q_id,
                    case_id=case_id,
                    track=track,
                    competency=comp,
                    topic=q_topic,
                    macro_dominio=macro,
                    micro_competencia=micro,
                    difficulty=q_diff,
                    question_type="SITUATIONAL",
                    stem=stem,
                    options_json=options,
                    correct_key=correct_key,
                    rationale=rat,
                    source_refs="Estatuto Tributario Colombiano",
                    is_verified=True,
                    hash_norm=h_norm
                )
                db.add(new_q)
                
        db.commit()
        print("✅ ¡Sincronización de nuevos casos completada exitosamente!")
    except Exception as e:
        db.rollback()
        print(f"🔥 Error al insertar nuevos casos: {e}")
    finally:
        db.close()

def main():
    # 1. SQLite Local
    insert_new_cases()
    
    # 2. Neon PostgreSQL
    neon_url = os.getenv("DATABASE_URL")
    if neon_url:
        print("\n🌐 Sincronizando con Neon PostgreSQL Cloud...")
        if neon_url.startswith("postgres://") or neon_url.startswith("postgresql://"):
            neon_url = neon_url.replace("postgres://", "postgresql+psycopg2://", 1)
            neon_url = neon_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            if "channel_binding=" in neon_url:
                import re
                neon_url = re.sub(r'[&?]channel_binding=[^&]*', '', neon_url)
                
        # Forzar el motor a usar Neon temporalmente cambiando la variable del session
        # Para hacerlo robusto y directo, creamos una transacción separada para Neon
        try:
            engine_neon = create_engine(neon_url)
            # Recreamos sessionmaker
            SessionNeon = sessionmaker(autocommit=False, autoflush=False, bind=engine_neon)
            db_neon = SessionNeon()
            
            # Repetimos lógica sobre Neon
            for case_data in NEW_CASES_DATA:
                case_id = case_data["id"]
                title = case_data["title"]
                text_content = case_data["text"]
                topic = case_data["topic"]
                diff = case_data["difficulty"]
                
                # Check exist
                existing_case = db_neon.query(CaseStudy).filter_by(id=case_id).first()
                if existing_case:
                    existing_case.title = title
                    existing_case.text = text_content
                    existing_case.topic = topic
                    existing_case.difficulty = diff
                else:
                    new_case = CaseStudy(
                        id=case_id,
                        title=title,
                        text=text_content,
                        topic=topic,
                        difficulty=diff
                    )
                    db_neon.add(new_case)
                    db_neon.flush()
                    
                for q_data in case_data["questions"]:
                    q_id = str(uuid.uuid4())
                    stem = q_data["stem"]
                    options = q_data["options"]
                    correct_key = q_data["correct_key"]
                    rat = q_data["rationale"]
                    track = q_data["track"]
                    comp = q_data["competency"]
                    q_topic = q_data["topic"]
                    macro = q_data["macro_dominio"]
                    micro = q_data["micro_competencia"]
                    q_diff = q_data["difficulty"]
                    
                    import hashlib
                    raw_norm = f"{stem} | {correct_key}"
                    h_norm = hashlib.md5(raw_norm.encode('utf-8')).hexdigest()
                    
                    existing_q = db_neon.query(Question).filter_by(hash_norm=h_norm).first()
                    if existing_q:
                        continue
                        
                    new_q = Question(
                        question_id=q_id,
                        case_id=case_id,
                        track=track,
                        competency=comp,
                        topic=q_topic,
                        macro_dominio=macro,
                        micro_competencia=micro,
                        difficulty=q_diff,
                        question_type="SITUATIONAL",
                        stem=stem,
                        options_json=options,
                        correct_key=correct_key,
                        rationale=rat,
                        source_refs="Estatuto Tributario Colombiano",
                        is_verified=True,
                        hash_norm=h_norm
                    )
                    db_neon.add(new_q)
            db_neon.commit()
            db_neon.close()
            print("✅ Sincronización exitosa con Neon Cloud.")
        except Exception as ne:
            print(f"❌ Error al sincronizar con Neon: {ne}")

if __name__ == "__main__":
    main()
