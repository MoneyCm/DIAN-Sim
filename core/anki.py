import genanki
import tempfile
import os
from typing import List

DIAN_MODEL_ID = 1583094822
DIAN_DECK_ID_BASE = 2026071300

FRONT_HTML = """
<div class="card-container">
  {{#Caso_Estudio}}
  <div class="caso-box">
    <div class="caso-titulo">Caso de Estudio</div>
    <div class="caso-texto">{{Caso_Estudio}}</div>
  </div>
  {{/Caso_Estudio}}

  {{#Tema}}
  <div class="badge-tema">{{Tema}}</div>
  {{/Tema}}

  <div class="pregunta-box">
    {{Pregunta}}
  </div>

  <div class="opciones-container">
    <button class="opcion-btn" id="btn-A" onclick="checkAnswer('A')">
      <span class="letra-circulo">A</span>
      <span class="texto-opcion">{{Opcion_A}}</span>
    </button>
    
    <button class="opcion-btn" id="btn-B" onclick="checkAnswer('B')">
      <span class="letra-circulo">B</span>
      <span class="texto-opcion">{{Opcion_B}}</span>
    </button>
    
    <button class="opcion-btn" id="btn-C" onclick="checkAnswer('C')">
      <span class="letra-circulo">C</span>
      <span class="texto-opcion">{{Opcion_C}}</span>
    </button>
    
    <button class="opcion-btn" id="btn-D" onclick="checkAnswer('D')">
      <span class="letra-circulo">D</span>
      <span class="texto-opcion">{{Opcion_D}}</span>
    </button>
  </div>

  <div id="correct-answer" style="display: none;">{{Respuesta_Correcta}}</div>
</div>

<script>
  (function() {
    const valD = "{{Opcion_D}}".trim();
    if (!valD || valD === "" || valD === "N/A" || valD === "None" || valD === "Opcion_D") {
      const btnD = document.getElementById("btn-D");
      if (btnD) btnD.style.display = "none";
    }
  })();

  function checkAnswer(selectedOption) {
    if (window.alreadyAnswered) return;
    window.alreadyAnswered = true;

    const correctAnswer = document.getElementById("correct-answer").innerText.trim().toUpperCase();
    const btnA = document.getElementById("btn-A");
    const btnB = document.getElementById("btn-B");
    const btnC = document.getElementById("btn-C");
    const btnD = document.getElementById("btn-D");
    
    const buttons = { 'A': btnA, 'B': btnB, 'C': btnC, 'D': btnD };

    Object.values(buttons).forEach(btn => {
      if (btn) btn.classList.add("disabled");
    });

    if (selectedOption === correctAnswer) {
      if (buttons[selectedOption]) buttons[selectedOption].classList.add("correct-choice");
    } else {
      if (buttons[selectedOption]) buttons[selectedOption].classList.add("incorrect-choice");
      if (buttons[correctAnswer]) buttons[correctAnswer].classList.add("correct-choice");
    }
  }
  window.alreadyAnswered = false;
</script>
"""

CSS_STYLE = """
.card {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #0f172a;
  color: #f1f5f9;
  text-align: left;
  font-size: 16px;
  line-height: 1.6;
  margin: 0;
  padding: 20px;
  display: flex;
  justify-content: center;
}

.card-container {
  max-width: 650px;
  width: 100%;
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  box-sizing: border-box;
}

.caso-box {
  background: rgba(15, 23, 42, 0.4);
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.caso-titulo {
  font-weight: 700;
  font-size: 12px;
  color: #38bdf8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.caso-texto {
  font-size: 14.5px;
  color: #cbd5e1;
}

.badge-tema {
  display: inline-block;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 6px 12px;
  border-radius: 20px;
  margin-bottom: 18px;
}

.pregunta-box {
  font-size: 18px;
  font-weight: 500;
  color: #f8fafc;
  margin-bottom: 24px;
  border-left: 4px solid #818cf8;
  padding-left: 14px;
}

.opciones-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.opcion-btn {
  display: flex;
  align-items: center;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 14px 18px;
  color: #cbd5e1;
  text-align: left;
  cursor: pointer;
  font-size: 15px;
  font-family: inherit;
  transition: all 0.2s ease;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.opcion-btn:hover:not(.disabled) {
  background: #334155;
  border-color: #6366f1;
  color: #ffffff;
  transform: translateY(-2px);
}

.letra-circulo {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #334155;
  color: #94a3b8;
  font-weight: 700;
  font-size: 13px;
  margin-right: 14px;
}

.opcion-btn:hover:not(.disabled) .letra-circulo {
  background: #6366f1;
  color: #ffffff;
}

.texto-opcion {
  flex-grow: 1;
}

.opcion-btn.disabled {
  cursor: default;
  pointer-events: none;
}

.opcion-btn.correct-choice {
  background: rgba(16, 185, 129, 0.15) !important;
  border-color: #10b981 !important;
  color: #a7f3d0 !important;
}
.opcion-btn.correct-choice .letra-circulo {
  background: #10b981 !important;
  color: #ffffff !important;
}

.opcion-btn.incorrect-choice {
  background: rgba(239, 68, 68, 0.15) !important;
  border-color: #ef4444 !important;
  color: #fca5a5 !important;
}
.opcion-btn.incorrect-choice .letra-circulo {
  background: #ef4444 !important;
  color: #ffffff !important;
}

.feedback-container {
  margin-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 24px;
  animation: fadeIn 0.4s ease-out;
}

.justificacion-box {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
  padding: 16px;
  border-left: 4px solid #10b981;
  margin-bottom: 16px;
}

.justificacion-titulo {
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
  color: #10b981;
  margin-bottom: 6px;
}

.justificacion-texto {
  font-size: 14.5px;
  color: #cbd5e1;
}

.norma-box {
  font-size: 12px;
  color: #64748b;
}

.norma-badge {
  background: #334155;
  color: #94a3b8;
  padding: 3px 8px;
  border-radius: 4px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
"""

BACK_HTML = """
<div class="card-container">
  {{#Caso_Estudio}}
  <div class="caso-box">
    <div class="caso-titulo">Caso de Estudio</div>
    <div class="caso-texto">{{Caso_Estudio}}</div>
  </div>
  {{/Caso_Estudio}}

  {{#Tema}}
  <div class="badge-tema">{{Tema}}</div>
  {{/Tema}}

  <div class="pregunta-box">
    {{Pregunta}}
  </div>

  <div class="opciones-container">
    <button class="opcion-btn disabled" id="btn-A">
      <span class="letra-circulo">A</span>
      <span class="texto-opcion">{{Opcion_A}}</span>
    </button>
    
    <button class="opcion-btn disabled" id="btn-B">
      <span class="letra-circulo">B</span>
      <span class="texto-opcion">{{Opcion_B}}</span>
    </button>
    
    <button class="opcion-btn disabled" id="btn-C">
      <span class="letra-circulo">C</span>
      <span class="texto-opcion">{{Opcion_C}}</span>
    </button>
    
    <button class="opcion-btn disabled" id="btn-D">
      <span class="letra-circulo">D</span>
      <span class="texto-opcion">{{Opcion_D}}</span>
    </button>
  </div>

  <div class="feedback-container">
    <div class="justificacion-box">
      <div class="justificacion-titulo">Justificación</div>
      <div class="justificacion-texto">{{Justificacion}}</div>
    </div>

    {{#Norma}}
    <div class="norma-box">
      <span>Referencia Normativa:</span>
      <span class="norma-badge">{{Norma}}</span>
    </div>
    {{/Norma}}
    {{#Regla_Clave}}
    <div class="justificacion-box">
      <div class="justificacion-titulo">Regla decisiva</div>
      <div class="justificacion-texto">{{Regla_Clave}}</div>
    </div>
    {{/Regla_Clave}}

    {{#Excepcion_Clave}}
    <div class="justificacion-box">
      <div class="justificacion-titulo">Excepción o límite</div>
      <div class="justificacion-texto">{{Excepcion_Clave}}</div>
    </div>
    {{/Excepcion_Clave}}

    {{#Distractor_Clave}}
    <div class="justificacion-box">
      <div class="justificacion-titulo">Distractor peligroso</div>
      <div class="justificacion-texto">{{Distractor_Clave}}</div>
    </div>
    {{/Distractor_Clave}}
  </div>

  <div id="correct-answer" style="display: none;">{{Respuesta_Correcta}}</div>
</div>

<script>
  (function() {
    const valD = "{{Opcion_D}}".trim();
    if (!valD || valD === "" || valD === "N/A" || valD === "None" || valD === "Opcion_D") {
      const btnD = document.getElementById("btn-D");
      if (btnD) btnD.style.display = "none";
    }

    const correctAnswer = document.getElementById("correct-answer").innerText.trim().toUpperCase();
    const btnA = document.getElementById("btn-A");
    const btnB = document.getElementById("btn-B");
    const btnC = document.getElementById("btn-C");
    const btnD = document.getElementById("btn-D");
    const buttons = { 'A': btnA, 'B': btnB, 'C': btnC, 'D': btnD };

    if (buttons[correctAnswer]) {
      buttons[correctAnswer].classList.add("correct-choice");
    }
  })();
</script>
"""

DIAN_FIELDS = [
    {"name": "Caso_Estudio"},
    {"name": "Tema"},
    {"name": "Pregunta"},
    {"name": "Opcion_A"},
    {"name": "Opcion_B"},
    {"name": "Opcion_C"},
    {"name": "Opcion_D"},
    {"name": "Respuesta_Correcta"},
    {"name": "Justificacion"},
    {"name": "Norma"},
    {"name": "Regla_Clave"},
    {"name": "Excepcion_Clave"},
    {"name": "Distractor_Clave"}
]

dian_model = genanki.Model(
    DIAN_MODEL_ID,
    'DIAN - Interactivo Enriquecido 13 Campos',
    fields=DIAN_FIELDS,
    templates=[
        {
            'name': 'Tarjeta Interactiva',
            'qfmt': FRONT_HTML,
            'afmt': BACK_HTML,
        },
    ],
    css=CSS_STYLE
)

def generate_anki_deck(questions: List[dict], deck_name: str) -> bytes:
    # Generar ID de mazo a partir del nombre para consistencia
    deck_id = DIAN_DECK_ID_BASE + abs(hash(deck_name)) % 100000
    
    dian_deck = genanki.Deck(deck_id, deck_name)
    
    for q in questions:
        # Sanitizar campos vacíos o nulos
        caso = str(q.get("Caso_Estudio", "") or "").strip()
        tema = str(q.get("Tema", "") or "").strip()
        preg = str(q.get("Pregunta", "") or "").strip()
        op_a = str(q.get("Opcion_A", "") or "").strip()
        op_b = str(q.get("Opcion_B", "") or "").strip()
        op_c = str(q.get("Opcion_C", "") or "").strip()
        op_d = str(q.get("Opcion_D", "") or "").strip()
        ans = str(q.get("Respuesta_Correcta", "") or "").strip().upper()
        just = str(q.get("Justificacion", "") or "").strip()
        norm = str(q.get("Norma", "") or "").strip()
        regla = str(q.get("Regla_Clave", "") or "").strip()
        excepcion = str(q.get("Excepcion_Clave", "") or "").strip()
        distractor = str(q.get("Distractor_Clave", "") or "").strip()
        
        note = genanki.Note(
            model=dian_model,
            fields=[caso, tema, preg, op_a, op_b, op_c, op_d, ans, just, norm, regla, excepcion, distractor]
        )
        dian_deck.add_note(note)
        
    # Guardar y escribir a bytes
    package = genanki.Package(dian_deck)
    
    # Usar tempfile para compilar
    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
    try:
        package.write_to_file(tmp_path)
        with open(tmp_path, "rb") as f:
            apkg_bytes = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return apkg_bytes
