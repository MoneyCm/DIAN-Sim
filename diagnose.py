import sys
import os
import datetime

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from db.session import SessionLocal
    from db.models import Question
    from core.generators.llm import LLMGenerator
    from core.gamification import get_rank_info
    import plotly.express as px
    import plotly.graph_objects as go
    print("✅ Imports successful (including get_rank_info and Plotly)")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_db():
    print("\n--- Testing Database Connection ---")
    try:
        db = SessionLocal()
        # Try a simple query
        count = db.query(Question).count()
        print(f"✅ DB connected successfully. Question count: {count}")
        db.close()
    except Exception as e:
        print(f"❌ DB connection error: {e}")

def test_llm():
    print("\n--- Testing LLM Generator (Gemini) ---")
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return

    try:
        gen = LLMGenerator("gemini", api_key)
        print("💡 Requesting questions from AI...")
        results = gen.generate_from_text("La DIAN es la entidad encargada de los impuestos en Colombia.", count=1)
        if results:
            print(f"✅ LLM generated {len(results)} questions successfully")
            print(f"First question: {results[0]['stem']}")
        else:
            print("❌ No questions generated")
    except Exception as e:
        print(f"❌ LLM error: {e}")

if __name__ == "__main__":
    test_db()
    test_llm()
