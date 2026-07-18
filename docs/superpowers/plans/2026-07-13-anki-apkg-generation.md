# Plan de Implementación: Generación Directa de Mazos Anki (.apkg)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar la generación y descarga directa de archivos `.apkg` de Anki en el simulador `dian_sim` mediante la librería `genanki`, permitiendo la importación de barajas interactivas en un solo clic.

**Architecture:** Módulo Python `core/anki.py` para definir el modelo de Anki de 10 campos con HTML/CSS interactivos. Integración en `app/pages/6_Dashboard.py` para exponer los botones de descarga de bytes en memoria utilizando archivos temporales.

**Tech Stack:** Python 3.13, Streamlit 1.54, SQLite / Postgres (SQLAlchemy), `genanki`.

## Global Constraints
* No utilizar dependencias binarias pesadas.
* El Tipo de Nota de Anki debe llamarse exactamente `DIAN - Interactivo 10 Columnas` y poseer IDs persistentes estables.
* El mazo debe ser 100% interactivo en dispositivos móviles (AnkiDroid/AnkiMobile) y de escritorio.

---

### Task 1: Agregar Dependencia `genanki`

**Files:**
* Modify: [requirements.txt](file:///c:/Proyectos/CesarWorkspace/dian_sim/requirements.txt)

**Interfaces:**
* Produces: `genanki` disponible en el entorno de Python.

- [ ] **Step 1: Modificar `requirements.txt`**
  Añadir `genanki` al final del archivo `requirements.txt`.
  ```diff
   stripe
  +genanki==0.13.0
   # Force rebuild v5
  ```

- [ ] **Step 2: Instalar dependencia**
  Run: `pip install genanki==0.13.0`
  Expected: Instalación exitosa.

- [ ] **Step 3: Verificar instalación**
  Run: `python -c "import genanki; print(genanki.__version__)"`
  Expected: `0.13.0` (o similar versión instalada sin excepciones).

- [ ] **Step 4: Commit**
  ```bash
  git add requirements.txt
  git commit -m "chore: add genanki dependency"
  ```

---

### Task 2: Crear el Módulo de Generación `core/anki.py`

**Files:**
* Create: [core/anki.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/core/anki.py)
* Create: [tests/test_anki_gen.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/tests/test_anki_gen.py)

**Interfaces:**
* Produces: `generate_anki_deck(questions: list, deck_name: str) -> bytes`

- [ ] **Step 1: Escribir el test unitario para verificar generación**
  Crear el archivo `tests/test_anki_gen.py` con el siguiente código:
  ```python
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
      print("✅ Prueba de generación de APKG exitosa.")

  if __name__ == "__main__":
      test_deck_generation()
  ```

- [ ] **Step 2: Ejecutar el test para verificar que falla**
  Run: `python tests/test_anki_gen.py`
  Expected: FAIL con `ModuleNotFoundError: No module named 'core.anki'`

- [ ] **Step 3: Implementar la lógica en `core/anki.py`**
  Crear el archivo `core/anki.py` con las plantillas interactivas y la lógica de genanki:
  ```python
  import genanki
  import tempfile
  import os
  from typing import List

  DIAN_MODEL_ID = 1583094821
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
      {"name": "Norma"}
  ]

  dian_model = genanki.Model(
      DIAN_MODEL_ID,
      'DIAN - Interactivo 10 Columnas',
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
          
          note = genanki.Note(
              model=dian_model,
              fields=[caso, tema, preg, op_a, op_b, op_c, op_d, ans, just, norm]
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
  ```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**
  Run: `python tests/test_anki_gen.py`
  Expected: PASS con el texto: `✅ Prueba de generación de APKG exitosa.`

- [ ] **Step 5: Commit**
  ```bash
  git add core/anki.py tests/test_anki_gen.py
  git commit -m "feat: implement genanki deck generator module"
  ```

---

### Task 3: Integrar en el Dashboard

**Files:**
* Modify: [app/pages/6_Dashboard.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/app/pages/6_Dashboard.py)

**Interfaces:**
* Consumes: `core.anki.generate_anki_deck`
* Produces: Dos nuevos botones `st.download_button` que devuelven el mazo de Anki `.apkg` para falladas y favoritas en la pestaña interactiva.

- [ ] **Step 1: Agregar el import de `generate_anki_deck` en `6_Dashboard.py`**
  Añadir el import debajo de los imports de core al principio del archivo (aproximadamente en la línea 15).
  ```python
  from core.anki import generate_anki_deck
  ```

- [ ] **Step 2: Modificar los bloques de descarga en la pestaña interactiva**
  En `6_Dashboard.py` (dentro del `with col_int1:` y `with col_int2:` en `tab_interactivo`), añadir el botón de descarga del APKG junto a la descarga de CSV:
  
  Modificar el bloque de fallas (`col_int1`):
  ```python
  with col_int1:
      st.markdown("##### ❌ Preguntas Falladas (Mazo Directo)")
      if failed_qs:
          # Convertir modelos a dicts para genanki
          failed_dicts = []
          for q in failed_qs:
              opts = q.options_json if q.options_json else {}
              caso_text = ""
              if q.case_study:
                  cs_title = f"({q.case_study.title})\n" if q.case_study.title else ""
                  caso_text = f"{cs_title}{q.case_study.text}"
              
              failed_dicts.append({
                  "Caso_Estudio": caso_text,
                  "Tema": q.topic,
                  "Pregunta": q.stem,
                  "Opcion_A": opts.get('A', ''),
                  "Opcion_B": opts.get('B', ''),
                  "Opcion_C": opts.get('C', ''),
                  "Opcion_D": opts.get('D', 'N/A'),
                  "Respuesta_Correcta": q.correct_key,
                  "Justificacion": q.rationale or 'N/A',
                  "Norma": q.source_refs or ''
              })
          
          # Generar mazo APKG
          failed_apkg = generate_anki_deck(failed_dicts, "DIAN - Fallas Interactivas")
          
          st.download_button(
              label="📥 Descargar Mazo APKG (Anki Directo)",
              data=failed_apkg,
              file_name=f"DIAN_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
              mime="application/apkg",
              use_container_width=True,
              key="btn_export_anki_fallas_apkg"
          )
          
          failed_int_csv = to_anki_interactive_csv(failed_qs)
          st.download_button(
              label="📥 Descargar Respuestas en CSV (Excel)",
              data=failed_int_csv,
              file_name=f"Anki_Dian_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
              mime="text/csv",
              use_container_width=True,
              key="btn_export_anki_fallas_int"
          )
          st.caption("Usa el botón APKG para importar todo en 1 clic. Usa el CSV si prefieres abrirlo en Excel.")
      else:
          st.info("No tienes fallas registradas todavía.")
  ```
  
  Modificar el bloque de favoritas (`col_int2`):
  ```python
  with col_int2:
      st.markdown("##### ⭐ Preguntas Favoritas (Mazo Directo)")
      if fav_qs:
          # Convertir modelos a dicts para genanki
          fav_dicts = []
          for q in fav_qs:
              opts = q.options_json if q.options_json else {}
              caso_text = ""
              if q.case_study:
                  cs_title = f"({q.case_study.title})\n" if q.case_study.title else ""
                  caso_text = f"{cs_title}{q.case_study.text}"
              
              fav_dicts.append({
                  "Caso_Estudio": caso_text,
                  "Tema": q.topic,
                  "Pregunta": q.stem,
                  "Opcion_A": opts.get('A', ''),
                  "Opcion_B": opts.get('B', ''),
                  "Opcion_C": opts.get('C', ''),
                  "Opcion_D": opts.get('D', 'N/A'),
                  "Respuesta_Correcta": q.correct_key,
                  "Justificacion": q.rationale or 'N/A',
                  "Norma": q.source_refs or ''
              })
          
          # Generar mazo APKG
          fav_apkg = generate_anki_deck(fav_dicts, "DIAN - Favoritas Interactivas")
          
          st.download_button(
              label="📥 Descargar Mazo APKG (Anki Directo)",
              data=fav_apkg,
              file_name=f"DIAN_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
              mime="application/apkg",
              use_container_width=True,
              key="btn_export_anki_favs_apkg"
          )
          
          fav_int_csv = to_anki_interactive_csv(fav_qs)
          st.download_button(
              label="📥 Descargar Respuestas en CSV (Excel)",
              data=fav_int_csv,
              file_name=f"Anki_Dian_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
              mime="text/csv",
              use_container_width=True,
              key="btn_export_anki_favs_int"
          )
          st.caption("Usa el botón APKG para importar todo en 1 clic. Usa el CSV si prefieres abrirlo en Excel.")
      else:
          st.info("No has marcado ninguna pregunta como favorita.")
  ```

- [ ] **Step 3: Actualizar las instrucciones visuales en `tab_interactivo`**
  Modificar el texto informativo inicial de la pestaña para guiar en el doble clic de APKG:
  ```python
      with tab_interactivo:
          st.info("""
          💡 **¿Cómo usar tus tarjetas interactivas en Anki en 1 solo clic?**
          1. Descarga el archivo de mazo directo **`.apkg`** usando los botones de abajo.
          2. Abre el archivo descargado haciendo **doble clic** en tu computadora.
          3. ¡Listo! Anki creará automáticamente la baraja y el diseño con botones interactivos.
          
          *Nota: Si prefieres configurar tu propia plantilla manualmente, puedes descargar el archivo `.csv` y seguir el mapeo tradicional de 10 columnas.*
          """)
  ```

- [ ] **Step 4: Probar localmente en Streamlit**
  Ejecutar la app local de Streamlit y descargar el archivo `.apkg` generado para validar que no haya excepciones de tipos ni importaciones.

- [ ] **Step 5: Commit**
  ```bash
  git add app/pages/6_Dashboard.py
  git commit -m "feat: integrate genanki download buttons and update UI instructions in Dashboard"
  ```
