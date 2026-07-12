import os
import sys
import uuid
import json
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.models import CaseStudy, Question

# Vocabulario de Combinación Semántica para la DIAN
EMPRESAS = [
    "Inversiones del Cauca S.A.S.", "Comercializadora Pacífico S.A.", "Consultores Integrales Ltda.",
    "Alimentos del Caribe S.A.S.", "Textiles Andinos S.A.", "Distribuidora Nacional de Insumos Ltda.",
    "Constructora del Eje S.A.S.", "Logística y Transporte Sabana S.A.", "Desarrollos Tecnológicos S.A.S.",
    "Compañía Minera del Centro Ltda.", "Suministros Industriales de Occidente S.A.", "Servicios Integrados de Frontera S.A.S.",
    "Importadora Global de Alimentos Ltda.", "Consorcio de Infraestructura Vial S.A.", "Metalúrgicas del Sur S.A.S.",
    "Plásticos y Empaques del Oriente Ltda.", "Agrícola del Tolima S.A.", "Comercio Mayorista de la Costa S.A.S.",
    "Servicios de Asesoría Integral S.A.S.", "Comercializadora de Frontera S.A."
]

PRODUCTOS = ["repuestos automotrices", "bienes de consumo", "químicos industriales", "insumos médicos", "textiles importados", "maquinaria pesada", "cereales y granos", "bienes tecnológicos", "materiales de construcción", "marcas y regalías extranjeras"]
CIUDADES = ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Cúcuta", "Ipiales", "Buenaventura", "Bucaramanga", "Pereira"]
MONTOS = [150, 280, 450, 620, 890, 1200, 2400, 3100, 4800, 5200] # Millones COP
ANOS = [2023, 2024, 2025]

# Definición de 8 Tópicos de Manual de Funciones del Gestor III
TOPICS_TEMPLATE = [
    {
        "type": "ANÁLISIS DE DENUNCIAS (Función 1)",
        "topic": "OPEC 236769 - Análisis Preliminar de Denuncias",
        "story": "La División de Fiscalización de la DIAN en {ciudad} recibe una denuncia de terceros bajo reserva de identidad contra la sociedad '{empresa}', dedicada a la comercialización de {producto}. La denuncia aporta pruebas de doble contabilidad y ventas omitidas por un valor estimado de COP {monto} millones en el año gravable {ano}. El gestor de la DIAN a cargo debe evaluar la pertinencia del inicio de una acción de fiscalización aplicando el análisis de congruencia y cruzando los estados financieros y exógena del RUT.",
        "questions": [
            {
                "topic": "Pertinencia de Denuncia",
                "stem": "SITUACIÓN: Tras evaluar la denuncia contra '{empresa}', el gestor de la DIAN comprueba que la exógena presenta inconsistencias sustanciales frente a lo denunciado. PREGUNTA: De acuerdo con los lineamientos de la DIAN, ¿cuál es el acto procesal inmediato a expedir si la denuncia cumple con los requisitos de pertinencia, veracidad y tiene mérito fiscal?",
                "options": {
                    "A": "Auto de Apertura de Investigación o Pliego de Cargos de Fiscalización.",
                    "B": "Liquidación Oficial de Revisión de Aforo Directo.",
                    "C": "Citación a conciliación previa obligatoria ante la Subdirección."
                },
                "correct_key": "A",
                "rationale": "Los lineamientos de fiscalización de la DIAN indican que si una denuncia presenta mérito ejecutivo e indicios claros de evasión, se expide un Auto de Apertura de Investigación para facultar al auditor a practicar visitas y requerir información."
            },
            {
                "topic": "Reserva de Identidad del Denunciante",
                "stem": "SITUACIÓN: El representante legal de '{empresa}' exige formalmente a la DIAN conocer el nombre de la persona que interpuso la denuncia de fiscalización en su contra. PREGUNTA: Conforme a la legislación de transparencia y el Estatuto Tributario, ¿cuál es el tratamiento legal que debe dar la DIAN a la identidad del denunciante?",
                "options": {
                    "A": "La DIAN debe mantener la reserva absoluta de la identidad del denunciante para garantizar su protección.",
                    "B": "La DIAN está obligada a revelar la identidad si el denunciado lo solicita por escrito bajo juramento.",
                    "C": "La DIAN debe remitir la identidad del denunciante a la Cámara de Comercio del municipio."
                },
                "correct_key": "A",
                "rationale": "La reserva de identidad de los denunciantes de fraude tributario está blindada por la ley de transparencia y las directrices institucionales de la DIAN para incentivar la colaboración ciudadana sin represalias."
            }
        ]
    },
    {
        "type": "PRECRÍTICA DE INSUMOS (Función 2)",
        "topic": "OPEC 236769 - Precrítica y Clasificación de Insumos",
        "story": "El Gestor III del área de Analítica y Programación de Fiscalización de la DIAN realiza la precrítica de las declaraciones del impuesto sobre la renta de la firma '{empresa}' por el año gravable {ano}. Al analizar el insumo de ingresos exógenos cruzados con retenciones en la fuente, el auditor detecta una discrepancia en costos de mano de obra de COP {monto} millones que no coincide con los aportes al sistema de seguridad social (UGPP). El auditor debe calificar el insumo y estructurar la pertinencia del pliego de cargos.",
        "questions": [
            {
                "topic": "Clasificación de Insumos",
                "stem": "SITUACIÓN: Durante la precrítica, el auditor de la DIAN determina que la inconsistencia en costos de '{empresa}' proviene de una inexactitud aritmética y no de un fraude doloso. PREGUNTA: Según los procedimientos de la DIAN, ¿cómo debe clasificar y priorizar este insumo para su posterior investigación?",
                "options": {
                    "A": "Debe clasificarse como Inexactitud de Corrección Inmediata y canalizarse mediante invitación persuasiva.",
                    "B": "Debe archivarse de inmediato por carecer de dolo o mala fe del contribuyente.",
                    "C": "Debe trasladarse a la Fiscalía General de la Nación como delito de concierto para delinquir."
                },
                "correct_key": "A",
                "rationale": "Los manuales de fiscalización de la DIAN priorizan las inconsistencias formales o aritméticas como temas persuasivos antes de iniciar un proceso de liquidación oficial de revisión costoso."
            },
            {
                "topic": "Requerimiento Ordinario de Información",
                "stem": "SITUACIÓN: Para confirmar los indicios de la precrítica de '{empresa}', el gestor de la DIAN decide requerir soportes de nómina electrónica. PREGUNTA: De acuerdo con el Artículo 684 del Estatuto Tributario, ¿bajo qué facultad legal de fiscalización actúa la DIAN al solicitar la exhibición de libros y soportes contables?",
                "options": {
                    "A": "Bajo la facultad general de fiscalización e investigación, mediante la notificación de un Requerimiento Ordinario.",
                    "B": "Bajo una orden judicial de allanamiento expedida por un juez de garantías penales.",
                    "C": "Bajo la acción extraordinaria de extinción de dominio sobre el archivo contable de la sociedad."
                },
                "correct_key": "A",
                "rationale": "El Artículo 684 del E.T. concede amplias facultades de fiscalización a la DIAN, entre ellas solicitar la exhibición de libros y soportes mediante requerimientos de información."
            }
        ]
    },
    {
        "type": "PROFERIR ACTOS ADMINISTRATIVOS (Función 6)",
        "topic": "OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo",
        "story": "La DIAN adelanta un proceso de determinación oficial contra la sociedad '{empresa}' por el año gravable {ano} tras identificar deducciones de pasivos inexistentes por COP {monto} millones. El Gestor III sustanciador debe redactar los actos administrativos de trámite, preparatorios y de fondo garantizando el debido proceso para evitar futuras nulidades ante la jurisdicción contencioso-administrativa.",
        "questions": [
            {
                "topic": "Término de Firmeza de Declaración",
                "stem": "SITUACIÓN: '{empresa}' presentó su declaración de renta del año {ano} con saldo a pagar y de forma oportuna. PREGUNTA: Conforme al Artículo 714 del Estatuto Tributario, ¿de cuánto tiempo dispone la DIAN para notificar el Requerimiento Especial antes de que la declaración adquiera firmeza general?",
                "options": {
                    "A": "Tres (3) años contados a partir del vencimiento del plazo para declarar o de su presentación extemporánea.",
                    "B": "Dos (2) años contados desde la presentación de la declaración en el banco receptor.",
                    "C": "Cinco (5) años contados desde la fecha de expedición de la firma digital de la declaración."
                },
                "correct_key": "A",
                "rationale": "El Artículo 714 del E.T. fija en tres (3) años el término general de firmeza de las declaraciones tributarias, período durante el cual la DIAN debe notificar el Requerimiento Especial."
            },
            {
                "topic": "Notificación Electrónica de Actos",
                "stem": "SITUACIÓN: El Gestor III de la DIAN notifica el Requerimiento Especial a '{empresa}' de forma electrónica a través del buzón del MUISCA. PREGUNTA: De acuerdo con el Artículo 566-1 del E.T., ¿en qué momento se entiende legalmente surtida la notificación enviada por medios electrónicos?",
                "options": {
                    "A": "A los cinco (5) días hábiles siguientes a la fecha en que el acto sea depositado en el buzón electrónico.",
                    "B": "El mismo día en que el contribuyente abra o ingrese efectivamente a leer la comunicación.",
                    "C": "A los diez (10) días calendario de haberse generado el correo de aviso de entrega."
                },
                "correct_key": "A",
                "rationale": "El Artículo 566-1 del E.T. estatuye de manera expresa que la notificación electrónica se entenderá surtida para todos los efectos legales a los cinco (5) días hábiles siguientes a su depósito en el buzón."
            }
        ]
    },
    {
        "type": "LAVADO DE ACTIVOS Y UIAF (Función 7)",
        "topic": "OPEC 236769 - Investigación de Lavado de Activos y Reporte UIAF",
        "story": "Durante una auditoría de control cambiario a la sociedad comercial '{empresa}' en {ciudad}, el investigador de la DIAN detecta giros atípicos de divisas hacia el extranjero por valor de COP {monto} millones sin justificación aduanera real. El dinero provenía de transferencias fraccionadas por debajo de los topes de declaración de calzado y {producto}. El auditor debe reportar las operaciones sospechosas y sustentar indicios de lavado de activos.",
        "questions": [
            {
                "topic": "Reporte de Operación Sospechosa (ROS)",
                "stem": "SITUACIÓN: Al consolidar los hallazgos de giros sospechosos de '{empresa}' a paraísos fiscales, el gestor de la DIAN proyecta un reporte inmediato. PREGUNTA: Ante indicios serios de lavado de activos o financiación del terrorismo, ¿a qué entidad nacional debe remitir la DIAN el Reporte de Operación Sospechosa (ROS)?",
                "options": {
                    "A": "A la Unidad de Información y Análisis Financiero (UIAF) de forma inmediata.",
                    "B": "A la Fiscalía General de la Nación mediante denuncia penal obligatoria.",
                    "C": "Al Banco de la República como administrador nacional de las divisas."
                },
                "correct_key": "A",
                "rationale": "Los servidores de la DIAN y del sector financiero deben reportar operaciones sospechosas de forma directa y reservada a la UIAF (Unidad de Información y Análisis Financiero) según las normas contra el lavado."
            },
            {
                "topic": "Reserva del Reporte de Operaciones",
                "stem": "SITUACIÓN: El representante legal de '{empresa}' interpone un derecho de petición exigiendo copia de los reportes enviados por la DIAN a la UIAF. PREGUNTA: De acuerdo con la normativa nacional de inteligencia financiera, ¿cómo debe responder la DIAN a esta solicitud de copias?",
                "options": {
                    "A": "Rechazar la solicitud de copia dado que los reportes ROS gozan de reserva legal absoluta y no pueden revelarse al investigado.",
                    "B": "Entregar copia física autenticada de todos los folios en salvaguarda del derecho de contradicción.",
                    "C": "Cobrar un arancel judicial de copias y remitir la información al correo del apoderado."
                },
                "correct_key": "A",
                "rationale": "Los reportes ROS a la UIAF gozan de reserva constitucional y legal absoluta para evitar alertar a las organizaciones criminales bajo sospecha de lavado."
            }
        ]
    },
    {
        "type": "PRACTICA DE PRUEBAS (Función 8)",
        "topic": "OPEC 236769 - Práctica de Pruebas e Inspección Tributaria",
        "story": "En medio del proceso de investigación a la sociedad '{empresa}' por inexactitudes contables de COP {monto} millones, la División de Liquidación solicita formalmente una visita técnica para verificar los inventarios físicos de {producto} en {ciudad}. El Gestor III investigador debe proferir el auto y adelantar la práctica de pruebas bajo las reglas procesales del régimen probatorio de la DIAN.",
        "questions": [
            {
                "topic": "Inspección Tributaria Auto",
                "stem": "SITUACIÓN: Para practicar la inspección de inventarios en '{empresa}', el gestor de la DIAN proyecta el auto correspondiente. PREGUNTA: De acuerdo con el Artículo 779 del Estatuto Tributario, ¿con qué acto administrativo formal se ordena una inspección tributaria y qué efecto produce sobre los términos de firmeza?",
                "options": {
                    "A": "Mediante Auto de Inspección Tributaria debidamente notificado, el cual suspende los términos para notificar el Requerimiento Especial por tres (3) meses.",
                    "B": "Mediante Oficio Ordinario de Visita, el cual interrumpe de forma definitiva los términos de prescripción del impuesto.",
                    "C": "Mediante Auto de Apertura de Pruebas, el cual no produce ningún tipo de efecto suspensivo de términos."
                },
                "correct_key": "A",
                "rationale": "El Artículo 779 del E.T. determina que la inspección tributaria se ordena mediante Auto y suspende por tres (3) meses el término para notificar el Requerimiento Especial, permitiendo una práctica probatoria completa."
            },
            {
                "topic": "Valor Probatorio de Libros",
                "stem": "SITUACIÓN: '{empresa}' presenta sus libros de contabilidad debidamente registrados, pero el auditor de la DIAN encuentra discrepancias con las facturas electrónicas de compras. PREGUNTA: De acuerdo con el Artículo 772 del Estatuto Tributario, ¿cuál es el valor probatorio general de los libros de contabilidad del contribuyente frente a la DIAN?",
                "options": {
                    "A": "Constituyen prueba a favor del contribuyente, siempre y cuando se lleven de acuerdo con las normas legales y soportes comprobatorios.",
                    "B": "No tienen valor probatorio y la DIAN puede desestimarlos a su arbitrio sin necesidad de justificación.",
                    "C": "Constituyen prueba plena e incontrovertible que impide a la DIAN reliquidar o modificar las declaraciones."
                },
                "correct_key": "A",
                "rationale": "El Artículo 772 del E.T. establece que la contabilidad del contribuyente es prueba a su favor si se lleva en debida forma con los correspondientes soportes facturados y comprobatorios."
            }
        ]
    }
]

def generate_100_cases():
    print("🚀 GENERANDO PROCEDIMENTALMENTE 100 CASOS DE ESTUDIO TIPO EXAMEN DIAN...")
    
    cases_batch = []
    
    # Generar combinaciones únicas
    used_combinations = set()
    
    count = 0
    while len(cases_batch) < 100:
        empresa = random.choice(EMPRESAS)
        producto = random.choice(PRODUCTOS)
        ciudad = random.choice(CIUDADES)
        monto = random.choice(MONTOS)
        ano = random.choice(ANOS)
        
        combo = (empresa, producto, ciudad, monto, ano)
        if combo in used_combinations:
            continue
        used_combinations.add(combo)
        
        # Seleccionar un tipo de tópico de forma cíclica
        template = TOPICS_TEMPLATE[count % len(TOPICS_TEMPLATE)]
        
        # Formatear el texto de la historia
        story_text = template["story"].format(
            empresa=empresa, producto=producto, ciudad=ciudad, monto=monto, ano=ano
        )
        
        case_id = f"case-procedural-{len(cases_batch)+1:03d}"
        case_title = f"Caso Protagónico {len(cases_batch)+1}: Fiscalización de {template['type']} - {empresa}"
        
        # Generar preguntas
        questions = []
        for i, q in enumerate(template["questions"]):
            stem = q["stem"].format(
                empresa=empresa, producto=producto, ciudad=ciudad, monto=monto, ano=ano
            )
            
            # Limpiar opciones
            opts = {}
            for k, v in q["options"].items():
                opts[k] = v.format(
                    empresa=empresa, producto=producto, ciudad=ciudad, monto=monto, ano=ano
                )
                
            q_topic = f"{template['topic']} - {q['topic']}"
            
            questions.append({
                "question_id": f"q-procedural-{len(cases_batch)+1:03d}-{i+1}",
                "stem": stem,
                "options": opts,
                "correct_key": q["correct_key"],
                "rationale": q["rationale"],
                "topic": q_topic,
                "track": "FUNCIONAL",
                "competency": template["type"].split("(")[0].strip(),
                "macro_dominio": "Tributario" if "Aduanero" not in template["story"] else "Aduanero",
                "micro_competencia": q["topic"]
            })
            
        cases_batch.append({
            "id": case_id,
            "title": case_title,
            "text": story_text,
            "topic": template["topic"],
            "difficulty": 3,
            "questions": questions
        })
        
        count += 1
        
    return cases_batch

def insert_cases_to_db(db_url, db_name, cases_data):
    print(f"\n🌐 Sincronizando con {db_name}...")
    try:
        engine = create_engine(db_url)
        # Recreamos sessionmaker
        SessionClass = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionClass()
        
        # Inserción rápida mediante transacciones eficientes
        case_count = 0
        q_count = 0
        
        for c in cases_data:
            # 1. Verificar si existe
            existing_case = db.query(CaseStudy).filter_by(id=c["id"]).first()
            if existing_case:
                existing_case.title = c["title"]
                existing_case.text = c["text"]
                existing_case.topic = c["topic"]
                existing_case.difficulty = c["difficulty"]
                case_id = existing_case.id
            else:
                new_case = CaseStudy(
                    id=c["id"],
                    title=c["title"],
                    text=c["text"],
                    topic=c["topic"],
                    difficulty=c["difficulty"]
                )
                db.add(new_case)
                db.flush()
                case_id = new_case.id
                case_count += 1
                
            # 2. Insertar preguntas del caso
            for q in c["questions"]:
                # Verificar hash o ID
                import hashlib
                raw_norm = f"{q['stem']} | {q['correct_key']}"
                h_norm = hashlib.md5(raw_norm.encode('utf-8')).hexdigest()
                
                existing_q = db.query(Question).filter_by(hash_norm=h_norm).first()
                if existing_q:
                    existing_q.case_id = case_id
                    existing_q.stem = q["stem"]
                    existing_q.options_json = q["options"]
                    existing_q.correct_key = q["correct_key"]
                    existing_q.rationale = q["rationale"]
                    existing_q.topic = q["topic"]
                    existing_q.track = q["track"]
                    existing_q.competency = q["competency"]
                    existing_q.macro_dominio = q["macro_dominio"]
                    existing_q.micro_competencia = q["micro_competencia"]
                else:
                    new_q = Question(
                        question_id=q["question_id"],
                        case_id=case_id,
                        track=q["track"],
                        competency=q["competency"],
                        topic=q["topic"],
                        macro_dominio=q["macro_dominio"],
                        micro_competencia=q["micro_competencia"],
                        difficulty=3,
                        question_type="SITUATIONAL",
                        stem=q["stem"],
                        options_json=q["options"],
                        correct_key=q["correct_key"],
                        rationale=q["rationale"],
                        source_refs="Estatuto Tributario Colombiano / Convocatoria DIAN 2676",
                        is_verified=True,
                        hash_norm=h_norm
                    )
                    db.add(new_q)
                    q_count += 1
                    
        db.commit()
        db.close()
        print(f"✅ Éxito en {db_name}: Se agregaron {case_count} casos y {q_count} preguntas situacionales.")
    except Exception as e:
        print(f"❌ Error en {db_name}: {e}")

def main():
    # 1. Generar los 100 casos procedimentales
    cases_generated = generate_100_cases()
    
    # 2. SQLite local
    sqlite_db_path = os.path.join(PROJECT_ROOT, "dian_sim.db")
    insert_cases_to_db(f"sqlite:///{sqlite_db_path}", "SQLite Local (dian_sim.db)", cases_generated)
    
    # 3. Neon PostgreSQL
    neon_url = os.getenv("DATABASE_URL")
    if neon_url:
        if neon_url.startswith("postgres://") or neon_url.startswith("postgresql://"):
            neon_url = neon_url.replace("postgres://", "postgresql+psycopg2://", 1)
            neon_url = neon_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            if "channel_binding=" in neon_url:
                import re
                neon_url = re.sub(r'[&?]channel_binding=[^&]*', '', neon_url)
        insert_cases_to_db(neon_url, "PostgreSQL Cloud (Neon)", cases_generated)
    else:
        print("\n⚠️ No se detectó DATABASE_URL en el entorno. Se omitió Neon Cloud.")

if __name__ == "__main__":
    main()
