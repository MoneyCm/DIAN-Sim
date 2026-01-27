
import os, sys
# Setup paths
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.generators.llm import LLMGenerator
from core.config import get_api_key

def demo_goa():
    provider = "gemini" # Using Gemini as default for demo
    api_key = get_api_key(provider)
    
    if not api_key:
        print("Error: No API Key found.")
        return

    # Simulation of "Régimen Simple de Tributación" text
    text = """
    El impuesto unificado bajo el régimen simple de tributación - SIMPLE es un modelo de tributación opcional de determinación integral, de declaración anual y pago bimestral, que sustituye el impuesto sobre la renta, e integra el impuesto nacional al consumo y el impuesto de industria y comercio consolidado, a cargo de los contribuyentes que opten voluntariamente por acogerse al mismo. El objetivo es reducir las cargas formales y sustanciales, impulsar la formalidad y facilitar el cumplimiento de las obligaciones tributarias.
    """
    
    generator = LLMGenerator(provider, api_key, goa_mode=True)
    results = generator.generate_from_text(text, count=1, difficulty=2)
    
    if results:
        q = results[0]
        stem = q['stem']
        word_count = len(stem.split())
        print("\n=== PREGUNTA GENERADA (Protocolo GOA 2667) ===")
        print(f"STEM: {stem}")
        print(f"\nCONTEO DE PALABRAS: {word_count}")
        print(f"OPCIONES: {q['options_json']}")
        print(f"CLAVE: {q['correct_key']}")
        print(f"JUSTIFICACIÓN: {q['rationale']}")
    else:
        print("No se generaron resultados.")

if __name__ == "__main__":
    demo_goa()
