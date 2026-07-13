import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.anki import generate_anki_deck

def test_deck_generation():
    dummy_questions = [
        {
            "Caso_Estudio": "Caso de prueba de la DIAN para verificar la facturación.",
            "Tema": "Facturación Electrónica",
            "Pregunta": "¿Cuál es el plazo máximo para transmitir la factura electrónica?",
            "Opcion_A": "48 horas",
            "Opcion_B": "24 horas",
            "Opcion_C": "72 horas",
            "Opcion_D": "N/A",
            "Respuesta_Correcta": "B",
            "Justificacion": "El decreto reglamentario indica un plazo máximo de 24 horas.",
            "Norma": "Decreto 358 de 2020 / Estatuto Tributario"
        }
    ]
    
    apkg_bytes = generate_anki_deck(dummy_questions, "DIAN - Test Deck")
    assert len(apkg_bytes) > 0, "Los bytes generados deben ser mayores a 0"
    print("Prueba de generacion de APKG exitosa.")

if __name__ == "__main__":
    test_deck_generation()
