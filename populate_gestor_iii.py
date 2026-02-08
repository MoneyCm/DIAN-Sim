
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal, engine
from db.models import Base, UserOPEC, Question
from core.generators.llm import LLMGenerator

def populate():
    print("🚀 Iniciando población para GESTOR III...")
    db: Session = SessionLocal()

    try:
        # 1. Update/Create OPEC Profile
        opec_data = {
            "opec_number": "236769",
            "job_title": "GESTOR III",
            "level": "Profesional",
            "grade": "3", # Adding this conceptually, though model might store in job_title or extra
            "purpose": "AT-FL-3006. DESARROLLAR, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, INVESTIGACIONES PARA LA VERIFICACION DEL CUMPLIMIENTO DE OBLIGACIONES EN MATERIA TRIBUTARIA, ADUANERA O CAMBIARIA, ASI COMO LA DETECCION DE PRACTICAS TENDIENTES A LA ELUSION, EVASION, ABUSO, CONTRABANDO Y LAVADO DE ACTIVOS, DE ACUERDO CON LA NORMATIVA VIGENTE, LOS PROCEDIMIENTOS ESTABLECIDOS Y LAS DIRECTRICES INSTITUCIONALES.",
            "functions": {
                "list": [
                    "HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION RECIBIDAS...",
                    "HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS RECIBIDOS...",
                    "ORGANIZAR LA INFORMACION Y PROPUESTAS DE ASUNTOS DE FISCALIZACION...",
                    "PARTICIPAR EN LA EJECUCION DE ACCIONES DE FISCALIZACION...",
                    "PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE...",
                    "REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO...",
                    "REALIZAR LA PRACTICA DE PRUEBAS SOLICITADAS...",
                    "REVISAR TECNICA Y O JURIDICAMENTE LOS EXPEDIENTES..."
                ]
            },
            "is_active": True
        }

        # Check existing
        existing_opec = db.query(UserOPEC).filter(UserOPEC.opec_number == "236769").first()
        if existing_opec:
            print(f"🔄 Actualizando OPEC {opec_data['opec_number']} existente.")
            existing_opec.job_title = opec_data["job_title"]
            existing_opec.purpose = opec_data["purpose"]
            existing_opec.functions = opec_data["functions"]["list"] # Store list directly
            existing_opec.is_active = True
        else:
            print(f"✨ Creando nueva OPEC {opec_data['opec_number']}.")
            new_opec = UserOPEC(
                opec_number=opec_data["opec_number"],
                job_title=opec_data["job_title"],
                level=opec_data["level"],
                purpose=opec_data["purpose"],
                functions=opec_data["functions"]["list"],
                is_active=True
            )
            db.add(new_opec)
        
        db.commit()
        print("✅ Perfil OPEC actualizado.")

        # 2. Generate Questions using Mistral
        print("🤖 Iniciando Generador IA (Mistral)...")
        
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            # Fallback hardcoded for this script session since passed by user
            mistral_key = "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13" 

        generator = LLMGenerator(provider="mistral", api_key=mistral_key, model_name="mistral-large-latest", goa_mode=True)

        context_text = f"""
        PERFIL: {opec_data['job_title']} (Grado {opec_data['grade']})
        PROPÓSITO: {opec_data['purpose']}
        FUNCIONES:
        """ + "\n- ".join(opec_data["functions"]["list"])

        print("⏳ Generando 10 preguntas situacionales... (puede tardar 30s)")
        questions = generator.generate_from_text(context_text, count=10, difficulty=3)

        # 3. Save to DB
        print(f"💾 Guardando {len(questions)} preguntas en base de datos...")
        count = 0
        import uuid
        from core.dedupe import compute_hash
        
        for q_data in questions:
            # Dedupe check
            h = q_data.get('hash_norm')
            if not db.query(Question).filter(Question.hash_norm == h).first():
                new_q = Question(
                    question_id=str(uuid.uuid4()),
                    track="COMPORTAMENTAL" if "COMPORTAMENTAL" in q_data.get('track', '').upper() else "FUNCIONAL",
                    macro_dominio=q_data.get('macro_dominio', 'Fiscalización'), # Default contextual
                    micro_competencia=q_data.get('micro_competencia', 'Gestión Tributaria'),
                    competency=q_data.get('competency', 'General'),
                    topic=f"OPEC {opec_data['opec_number']} - Fiscalización",
                    difficulty=3,
                    stem=q_data.get('stem'),
                    options_json=q_data.get('options_json'),
                    correct_key=q_data.get('correct_key'),
                    rationale=q_data.get('rationale'),
                    source_refs="Autogenerado Script GESTOR III",
                    created_at=datetime.utcnow(),
                    hash_norm=h
                )
                db.add(new_q)
                count += 1
        
        db.commit()
        print(f"🎉 ¡Éxito! Se guardaron {count} preguntas nuevas para GESTOR III.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate()
