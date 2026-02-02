
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import func, and_
import pandas as pd

# Load env vars
load_dotenv()

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import Question
from core.profiles import PROFILES

def analyze():
    print("📊 Analizando Balanceo para GESTOR III (OPEC 236769)...")
    
    target_profile = PROFILES["Gestor III (OPEC 236769)"]
    
    # 1. Definir Metas (Buckets)
    # Lista plana de todos los temas requeridos
    required_topics = []
    
    # Funcionales
    for track, topics in target_profile["functional_tracks"].items():
        for t in topics:
            required_topics.append({"topic": t, "type": track})
            
    # Comportamentales
    for c in target_profile["behavioral_competencies"]:
        required_topics.append({"topic": c, "type": "COMPORTAMENTAL"})
        
    print(f"🎯 Temas Requeridos: {len(required_topics)}")
    
    # 2. Consultar DB
    db = SessionLocal()
    
    # Estructura para guardar conteos: { "Tema": { 1: count, 2: count, 3: count } }
    matrix = {}
    
    for item in required_topics:
        topic = item["topic"]
        matrix[topic] = {1: 0, 2: 0, 3: 0, "type": item["type"]}
        
        # Consultar por tema (usando ilike para flexibilidad)
        # Nota: Gestor III busca principalmente por match de Texto, pero aquí validamos si el tema existe
        
        # Query: Topic match specific to Gestor III scope? 
        # Or just general topic match? 
        # Given we want to balance specific topics, we check if the question belongs to the topic.
        # We also prioritize questions that are "Gestor III" specific if possible, but general questions work too.
        
        for diff in [1, 2, 3]:
            # Count
            c = db.query(Question).filter(
                and_(
                    Question.topic.ilike(f"%{topic}%"),
                    Question.difficulty == diff
                )
            ).count()
            matrix[topic][diff] = c
            
    db.close()
    
    # 3. Reportar Brechas
    TARGET_PER_BUCKET = 3 # Start low to see results
    
    print("\n| Tema / Competencia | Tipo | Dif 1 (Básico) | Dif 2 (Interm) | Dif 3 (Avanz) | Total |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    total_gaps = 0
    
    for topic in matrix:
        data = matrix[topic]
        t_type = data["type"]
        d1 = data[1]
        d2 = data[2]
        d3 = data[3]
        total = d1 + d2 + d3
        
        # Color code format for console/markdown
        def fmt(val):
            return f"**{val}**" if val >= TARGET_PER_BUCKET else f"{val} (Faltan {TARGET_PER_BUCKET - val})"
            
        print(f"| {topic} | {t_type} | {fmt(d1)} | {fmt(d2)} | {fmt(d3)} | {total} |")
        
        calc_gap = max(0, TARGET_PER_BUCKET - d1) + max(0, TARGET_PER_BUCKET - d2) + max(0, TARGET_PER_BUCKET - d3)
        total_gaps += calc_gap

    print(f"\n📉 **Brecha Total:** Se necesitan generar **{total_gaps}** preguntas nuevas para llegar al 'Equilibrio Base' ({TARGET_PER_BUCKET} por nivel).")

if __name__ == "__main__":
    analyze()
