
import sys
import os
import time
import uuid
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import Question, UserOPEC, UserAPIKey
from core.generators.llm import LLMGenerator
from core.security_keys import decrypt_value
from sqlalchemy import func

PROVIDERS = ["groq", "mistral", "gemini"]

def get_generator(provider_name):
    """Initialize generator with specific provider safely"""
    try:
        api_key = None
        # 1. Try Env
        if provider_name == "groq":
            api_key = os.getenv("GROQ_API_KEY")
        elif provider_name == "mistral":
            api_key = os.getenv("MISTRAL_API_KEY")
        elif provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            
        # 2. Try DB if Env missing
        if not api_key:
            db = SessionLocal()
            try:
                # Get the most recent key for this provider
                entry = db.query(UserAPIKey).filter(
                    UserAPIKey.provider == provider_name
                ).order_by(UserAPIKey.id.desc()).first()
                
                if entry:
                    api_key = decrypt_value(entry.encrypted_key)
                    if api_key:
                        print(f"🔑 Found {provider_name} key in DB.")
            except Exception as dbe:
                print(f"⚠️ DB Key lookup failed: {dbe}")
            finally:
                db.close()
            
        if not api_key:
            print(f"⚠️ No API Key for {provider_name} (Env or DB), skipping.")
            return None
            
        print(f"🤖 Initializing LLM with {provider_name}...")
        return LLMGenerator(provider=provider_name, api_key=api_key)
    except Exception as e:
        print(f"❌ Error init {provider_name}: {e}")
        return None

def seed_massive():
    db = SessionLocal()
    
    # 1. Determine Context
    active_opec = db.query(UserOPEC).filter_by(is_active=True).first()
    if active_opec:
        job_title = active_opec.job_title
        print(f"🎯 Targeting Active OPEC: {job_title}")
    else:
        job_title = "Gestor II"
        print(f"🎯 Targeting Default: {job_title}")

    # 2. Init Strategy
    current_provider_idx = 0
    gen = get_generator(PROVIDERS[current_provider_idx])
    
    # Failover if first choice invalid
    while not gen and current_provider_idx < len(PROVIDERS) - 1:
        current_provider_idx += 1
        gen = get_generator(PROVIDERS[current_provider_idx])
        
    if not gen:
        print("❌ No valid providers found. Check .env")
        return

    # 3. Targets
    targets = [
        {"track": "COMPORTAMENTAL", "goal": 200, "batch_size": 5},
        {"track": "INTEGRIDAD", "goal": 200, "batch_size": 5}
    ]

    for target in targets:
        track = target["track"]
        goal = target["goal"]
        batch_size = target["batch_size"]
        
        while True:
            # Check Count
            try:
                current_count = db.query(Question).filter(
                    Question.track == track,
                    Question.topic.ilike(f'%{job_title}%')
                ).count()
            except Exception as e:
                print(f"⚠️ DB Error reading count: {e}")
                time.sleep(5)
                continue
            
            print(f"📊 {track}: {current_count}/{goal} | Using: {PROVIDERS[current_provider_idx]}")
            
            if current_count >= goal:
                print(f"✅ {track} goal reached!")
                break
                
            # Generate
            needed = min(batch_size, goal - current_count)
            prompt_context = ""
            if track == "COMPORTAMENTAL":
                prompt_context = f"Generar preguntas de situación comportamental (Liderazgo, Trabajo en Equipo, Orientación al Usuario) para el cargo {job_title}."
            elif track == "INTEGRIDAD":
                prompt_context = f"Generar preguntas de dilemas éticos, código de integridad y valores para el cargo {job_title}."
            
            try:
                # Attempt Generation
                questions = gen.generate_from_text(prompt_context, count=needed, difficulty=2)
                
                # Save
                saved_count = 0
                for q in questions:
                    new_q = Question(
                        question_id=str(uuid.uuid4()),
                        stem=q.get("stem"),
                        options_json=q.get("options"),
                        correct_key=q.get("correct_key"),
                        rationale=q.get("rationale"),
                        track=track,
                        topic=f"{job_title} - {track.capitalize()}",
                        competency=track.capitalize(),
                        micro_competencia="Competencia Blanda",
                        macro_dominio="Competencias Comunes",
                        difficulty=2,
                        hash_norm=str(uuid.uuid4())
                    )
                    db.add(new_q)
                    saved_count += 1
                
                db.commit()
                print(f"💾 Saved {saved_count} questions.")
                
            except Exception as e:
                print(f"⚠️ Error with {PROVIDERS[current_provider_idx]}: {e}")
                
                # FAILOVER LOGIC
                print("🔄 Switching provider...")
                original_idx = current_provider_idx
                
                # Find next valid provider
                found_new = False
                for _ in range(len(PROVIDERS) - 1):
                    current_provider_idx = (current_provider_idx + 1) % len(PROVIDERS)
                    print(f"   Trying {PROVIDERS[current_provider_idx]}...")
                    gen = get_generator(PROVIDERS[current_provider_idx])
                    if gen:
                        found_new = True
                        break
                
                if not found_new:
                    print("❌ All providers failed. Waiting 60s...")
                    time.sleep(60)
                    # Try original again
                    current_provider_idx = original_idx
                    gen = get_generator(PROVIDERS[current_provider_idx])

            # Rate Limit Sleep
            time.sleep(2)

    db.close()
    print("🎉 Massive Seeding Complete!")

if __name__ == "__main__":
    seed_massive()
