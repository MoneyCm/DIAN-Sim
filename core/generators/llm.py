import os
import json
import uuid
import datetime
import time
from typing import List
from db.models import Question
from core.dedupe import compute_hash
import openai
from google import genai
from google.genai import types
from core.normativa import NormativaManager
from core.config import get_api_key
from .utils import repair_and_parse_json
# from mistralai import Mistral # Moved to lazy import


LLM_AUDIT_RUNTIME_VERSION = "safe-fallback-v2"


class LLMGenerator:
    DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_MODEL_FALLBACKS = ("gemini-2.5-flash", "gemini-flash-latest")

    def __init__(self, provider: str, api_key: str, model_name: str = None, goa_mode: bool = True):
        self.provider = provider.lower()
        self.api_key = api_key.strip() if api_key else ""
        self.model_name = model_name
        self.goa_mode = goa_mode
        
        # Try to initialize both if possible (for fallbacks)
        self.openai_client = None
        self.gemini_client = None
        self.mistral_client = None
        self.fallback_client = None
        self.fallback_type = "openai"

        # Primary Client
        if self.provider == "openai" and self.api_key:
            self.openai_client = openai.OpenAI(api_key=self.api_key)
        elif self.provider == "gemini" and self.api_key:
            self.gemini_client = genai.Client(api_key=self.api_key)
        elif self.provider == "groq" and self.api_key:
            self.openai_client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        elif self.provider == "mistral" and self.api_key:
            try:
                from mistralai import Mistral
                self.mistral_client = Mistral(api_key=self.api_key)
            except ImportError:
                print("⚠️ MistralAI not installed.")
                self.mistral_client = None

        # Fallback Clients (v44 Mikey: Universal Shield)
        if self.provider == "gemini":
            # Si somos Gemini, preparemos Groq/OpenAI como respaldo secreto
            for fb_provider in ["groq", "openai"]:
                fb_key = get_api_key(fb_provider)
                if fb_key:
                    try:
                        if fb_provider == "groq":
                            self.fallback_client = openai.OpenAI(
                                api_key=fb_key,
                                base_url="https://api.groq.com/openai/v1"
                            )
                            self.fallback_type = "groq"
                        else:
                            self.fallback_client = openai.OpenAI(api_key=fb_key)
                            self.fallback_type = "openai"
                        print(f"✅ Fallback {fb_provider} configurado exitosamente. Mikey v47.1")
                        break 
                    except:
                        pass
            

    def generate_from_text(self, text: str, count: int = 5, difficulty: int = 2, progress_callback=None, user_id: int = None) -> List[dict]:
        """Generates questions by splitting into smarter segments with v47 logic. Mikey"""
        self.user_id = user_id 
        all_results = []
        batch_size = 5 
        text_len = len(text)
        
        # Determine number of batches
        remaining = count
        total_batches = (count + batch_size - 1) // batch_size
        
        # v47.2 Supernova: Context Compression for Massive Files
        window_size = 18000
        if text_len > 1000000:
            window_size = 12000 # Compact context for free tier limit avoidance
            print(f"DEBUG: Massive File Detected ({text_len} chars). Compressing window to {window_size}. Mikey v47.2")
        
        overlap = 2000 # Small overlap to keep context
        
        coverage_mode = "sampling"
        if (total_batches * (window_size - overlap)) >= text_len:
            coverage_mode = "full_coverage"
            print(f"DEBUG: Active Mode: FULL COVERAGE (Text: {text_len} chars). Mikey v47")
        else:
            print(f"DEBUG: Active Mode: SAMPLING (Text: {text_len} chars). Mikey v47")

        for i in range(total_batches):
            current_batch = min(remaining, batch_size)
            
            if progress_callback:
                pct = int((i / total_batches) * 100)
                progress_callback(pct, f"Generando lote {i+1} de {total_batches} ({coverage_mode})...")

            if coverage_mode == "full_coverage":
                start = i * (window_size - overlap)
                end = min(start + window_size, text_len)
            else:
                # Sampling: Spread batches throughout the document
                step = text_len // (total_batches + 1)
                start = i * step
                end = min(start + window_size, text_len)
            
            # v47 Semantic Adjustment: Find a paragraph break near the end if possible
            if end < text_len:
                next_break = text.find("\n\n", end - 500, end + 500)
                if next_break != -1:
                    end = next_break
            
            batch_text = text[start:end]
                
            print(f"DEBUG: Gen Batch {i+1}/{total_batches} (Qs: {current_batch}) | Range: [{start}:{end}]. Mikey v47")
            try:
                batch_results = self._generate_batch(batch_text, current_batch, difficulty)
                all_results.extend(batch_results)
                remaining -= current_batch
                if remaining > 0:
                    time.sleep(1)
            except Exception as e:
                print(f"ERROR: Batch {i} failed: {type(e).__name__}")
                if all_results: break
                else: raise e
                    
        return all_results

    def _generate_batch(self, text: str, count: int = 5, difficulty: int = 2) -> List[dict]:
        # Fetch OPEC context if available
        opec_context = ""
        try:
            from db.session import SessionLocal
            from db.models import UserOPEC
            db = SessionLocal()
            # Filter by specific user if provided Mikey
            if hasattr(self, 'user_id') and self.user_id:
                active_opec = db.query(UserOPEC).filter_by(user_id=self.user_id, is_active=True).first()
            else:
                active_opec = db.query(UserOPEC).filter_by(is_active=True).first()
            if active_opec:
                opec_context = f"\nCARGO OBJETIVO: {active_opec.job_title} (Nivel {active_opec.level})\n"
                opec_context += f"PROPÓSITO: {active_opec.purpose}\n"
                if active_opec.functions:
                    opec_context += "FUNCIONES CLAVE A EVALUAR:\n- " + "\n- ".join(active_opec.functions[:10]) + "\n"
            db.close()
        except Exception as e:
            print(f"DEBUG: Error fetching OPEC context: {type(e).__name__}")

        # The supplied document is the only normative authority for question
        # generation. Automatic RAG results can be useful for tutoring, but here
        # they may introduce rules that are absent from the user's source.
        normativa_context = ""

        # Fetch Behavioral Competencies (Res 65) - v48 Mikey
        behavioral_context = ""
        try:
            res_65_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "res_65_competencias.json")
            if os.path.exists(res_65_path):
                with open(res_65_path, "r", encoding="utf-8") as f:
                    comp_data = json.load(f)
                    behavioral_context = "\nMARCO DE COMPETENCIAS COMPORTAMENTALES (Resolución 0065 DIAN):\n"
                    # Add common competencies definitions
                    for key, val in comp_data.get("common_competencies", {}).items():
                        behavioral_context += f"- {val['name']}: {val['definition']}\n"
                        # Add Level 3 indicators specifically for Gestor III
                        if "3" in val.get("levels", {}):
                            behavioral_context += f"  Conductas Nivel 3 (Profesional): {'; '.join(val['levels']['3'])}\n"
                    print(f"DEBUG: Loaded Behavioral Context ({len(behavioral_context)} chars). Mikey v48")
        except Exception as e:
            print(f"DEBUG: Error loading Res 65 context: {type(e).__name__}")

        # Situational-practice logic. This is an internal quality standard, not
        # a claim about an unpublished or external CNSC item template.
        goa_instr = ""
        if self.goa_mode:
            goa_instr = """
        REQUISITOS DE PRÁCTICA SITUACIONAL (estándar interno de calidad):
        1. ESTRUCTURA DE JUICIO SITUACIONAL: 
           - CASO (Contexto): Un párrafo de 80-120 palabras que describa una situación laboral REALISTA en la DIAN. Incluye variables técnicas y distractores contextuales (ruido).
           - ENUNCIADO (Stem): Una pregunta que cierre el caso (ej: "Ante este escenario, la acción correcta del gestor es..."). debe estar integrado al final del caso.
        2. OPCIONES DE RESPUESTA: DEBEN SER EXACTAMENTE TRES (3). A, B y C. No generes opción D.
        3. CALIDAD DE OPCIONES:
           - Clave: La respuesta técnica o conductualmente correcta según la norma.
           - Distractor 1: Opción plausible pero que omite un requerimiento legal o paso procedimental.
           - Distractor 2: Opción que parece eficiente/rápida pero viola la norma o el protocolo ético.
        4. TAXONOMÍA OBLIGATORIA:
           - Macro-Dominio: Clasifica en (Tributario, Aduanero, Cambiario, Transversal, Comportamental, Integridad).
           - Micro-Competencia: Identifica el tema específico (ej: "Procedimiento de Cobro", "Régimen Simple", "Adaptabilidad").
            """
        else:
            goa_instr = """
        REQUISITOS DE GENERACIÓN TÉCNICA (Directo):
        1. ENUNCIADO DIRECTO: Una pregunta clara y técnica. Sin preámbulos de casos.
        2. OPCIONES: EXACTAMENTE TRES (A, B, C). Solo una es la clave técnica.
        3. CALIDAD: Usa terminología de la DIAN (Estatuto Tributario, Resoluciones, etc.).
        4. TAXONOMÍA OBLIGATORIA: Clasifica siempre en track (FUNCIONAL/COMPORTAMENTAL), macro_dominio y micro_competencia.
            """

        # Context definition v46 Mikey
        context = text[:15000]
        
        prompt = f"""
        Actúa como editor especializado en material de práctica basado en normativa aplicable a la DIAN.
        Tu misión es generar EXACTAMENTE {count} preguntas FUNCIONALES de selección múltiple con DIFICULTAD EDITORIAL INTERNA {difficulty}/10.
        Rúbrica: 1-2 reconocimiento/comprensión; 3-4 aplicación; 5-6 integración y análisis; 7-8 juicio avanzado; 9-10 transferencia compleja. Esta no es una escala oficial de la CNSC.
        
        REGLA DE ORO DE ENTIDAD:
        * El protagonista siempre trabaja para la DIAN (Dirección de Impuestos y Aduanas Nacionales).
        * NUNCA menciones a la CNSC (Comisión Nacional del Servicio Civil) como el empleador. La CNSC solo convoca el concurso externo, pero el rol laboral ocurre dentro de la DIAN.
        * Usa EXCLUSIVAMENTE hechos, reglas y excepciones presentes en el TEXTO DE REFERENCIA.
        * Si el texto no permite sustentar una pregunta, devuelve {{"questions": []}}. No completes vacíos con conocimiento externo.
        
        {opec_context}
        {normativa_context}
        {behavioral_context}
        
        {goa_instr}

        TEXTO DE REFERENCIA:
        "{context}..."
        
        FORMATO DE SALIDA (Objeto JSON obligatorio):
        {{
          "questions": [
            {{
              "track": "FUNCIONAL",
              "macro_dominio": "Macro-Dominio detectado",
              "micro_competencia": "Micro-Competencia detectada",
              "topic": "tema resumido",
              "difficulty": {difficulty},
              "stem": "SITUACIÓN: [Caso de 80-120 palabras]. PREGUNTA: [Enunciado táctico]?",
              "options": {{
                "A": "Opción 1",
                "B": "Opción 2",
                "C": "Opción 3"
              }},
              "correct_key": "Letra correcta",
              "rationale": "Justificación basada en el Artículo [X] del Estatuto Tributario o norma específica aplicada al caso."
            }}
          ]
        }}
        
        IMPORTANTE: No respondas con nada que no sea el JSON. La densidad léxica debe ser técnica (Acto Administrativo, Título Ejecutivo, Sujeto Pasivo, etc.).
        """
        
        try:
            content = ""
            if self.provider == "openai" and self.openai_client:
                model = self.model_name if self.model_name else "gpt-4o-mini"
                print(f"DEBUG: Enviando lote a OpenAI ({model})...")
                try:
                    response = self.openai_client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Edita material de práctica basado únicamente en la fuente suministrada. "
                                    "No afirmes representar a la DIAN ni a la CNSC. Genera exclusivamente JSON válido."
                                ),
                            },
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    content = response.choices[0].message.content
                except Exception as e:
                    if "insufficient_quota" in str(e):
                        raise Exception("❌ Saldo insuficiente en OpenAI. Por favor, recarga tu cuenta o usa Gemini/Groq (Gratuitos).")
                    raise e
                
            elif self.provider == "groq" and self.openai_client:
                # Groq es extremadamente rápido con Llama 3
                print(f"DEBUG: Enviando lote a Groq (Llama 3.3)...")
                response = self.openai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Actúa como un generador de JSON. Responde únicamente con el objeto JSON solicitado."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content

            elif self.provider == "mistral" and self.mistral_client:
                # Mistral La Large
                print(f"DEBUG: Enviando lote a Mistral ({self.model_name or 'mistral-large-latest'})...")
                response = self.mistral_client.chat.complete(
                    model=self.model_name if self.model_name else "mistral-large-latest",
                    messages=[
                        {"role": "system", "content": "Actúa como un generador de JSON. Responde únicamente con el objeto JSON solicitado."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                if response and response.choices:
                    content = response.choices[0].message.content
                
            elif self.provider == "gemini":
                # v43 Mikey: New SDK candidates
                candidates = list(self.GEMINI_MODEL_FALLBACKS)
                
                # If specialized model requested
                if self.model_name:
                    clean_name = self.model_name.replace("models/", "")
                    if clean_name in candidates:
                        candidates.remove(clean_name)
                    candidates.insert(0, clean_name)
                
                content = ""
                last_error = None
                
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    ]
                )
                
                for model_name in candidates:
                    try:
                        print(f"DEBUG: Enviando lote a Gemini ({model_name})... Mikey v44")
                        response = self.gemini_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            content = response.text
                            break
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            print(f"[429] Cuota excedida en {model_name}.")
                            raise e 
                        
                        print(
                            f"DEBUG: Error Gemini {model_name}: "
                            f"{type(e).__name__}"
                        )
                        continue
                
                # v47.1 Validation & Rescue Mikey (if needed for non-429 failures)
                
                # v47.1 Validation & Rescue Mikey
                if not content and hasattr(self, 'fallback_client') and self.fallback_client:
                    fb_t = getattr(self, 'fallback_type', 'openai')
                    print(f"⚠️ [v47.1] Gemini falló. Activando RESCATE con {fb_t}... Mikey")
                    try:
                        fb_model = "gpt-4o-mini" if fb_t == "openai" else "llama-3.3-70b-versatile"
                        fb_response = self.fallback_client.chat.completions.create(
                            model=fb_model,
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"}
                        )
                        content = fb_response.choices[0].message.content
                    except Exception as fe:
                        print(
                            f"❌ Falló incluso el rescate {fb_t}: "
                            f"{type(fe).__name__}"
                        )

                if not content:
                    raise Exception(f"Falla total v47.1 Mikey: La IA no devolvió contenido tras {len(candidates)} intentos y rescate.")

                # Cleanup markdown
                if "```json" in content:
                    content = content.replace("```json", "").split("```")[0]
                elif "```" in content:
                    content = content.replace("```", "")
        
            # v47 JSON Repair Célula Mikey
            data = repair_and_parse_json(content)
            if not data:
                raise Exception("Fallo crítico: El contenido de la IA no pudo ser parseado como JSON tras reparación.")

            # Extract candidates
            candidates = []
            if isinstance(data, dict):
                if "questions" in data:
                    candidates = data["questions"]
                elif len(data.keys()) == 1:
                    candidates = list(data.values())[0]
                else:
                    if "stem" in data:
                        candidates = [data]
            elif isinstance(data, list):
                candidates = data
                
            if not candidates or not isinstance(candidates, list):
                raise Exception("No se encontraron preguntas en la respuesta del lote.")
                
            # Convert to internal Dict structure
            results = []
            for item in candidates:
                if not item.get("stem"):
                    continue
                    
                q_dict = {
                    "question_id": str(uuid.uuid4()),
                    "track": item.get("track", "FUNCIONAL"),
                    "macro_dominio": item.get("macro_dominio", "Transversal"),
                    "micro_competencia": item.get("micro_competencia", item.get("competency", "General")),
                    "competency": item.get("competency", item.get("micro_competencia", "General")),
                    "topic": item.get("topic", "Generado por IA"),
                    "difficulty": item.get("difficulty", difficulty),
                    "stem": item.get("stem"),
                    "options_json": item.get("options"),
                    "correct_key": item.get("correct_key"),
                    "rationale": item.get("rationale"),
                    "source_refs": "Generado desde Texto Usuario",
                    "hash_norm": compute_hash(item.get("stem", ""))
                }
                results.append(q_dict)
                
            return results
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit_exceeded" in error_msg:
                if self.provider == "groq":
                    raise Exception("Límite diario de Groq alcanzado (TPD). Por favor, espera a que se reinicie tu cuota o usa Google Gemini como alternativa gratuita más estable.")
                if self.provider == "gemini":
                    raise Exception(
                        "La cuota diaria de Gemini está agotada. Espera a que se restablezca "
                        "o selecciona Mistral en la configuración del generador."
                    )
                else:
                    raise RuntimeError(
                        "Límite de velocidad del proveedor alcanzado. Inténtalo más tarde."
                    ) from e
            raise RuntimeError(
                f"No se pudo completar el lote con {self.provider or 'el proveedor configurado'}."
            ) from e

    def explain_socratically(self, question_data: dict) -> str:
        """Orienta el razonamiento sin revelar ni recalificar la respuesta."""
        from core.socratic_tutor import build_socratic_prompt

        prompt = build_socratic_prompt(
            competition=question_data.get("competition", "Concurso activo"),
            stem=question_data.get("stem", ""),
            options=question_data.get("options_json", {}),
            selected_key=question_data.get("selected_key", "Sin respuesta"),
            rationale=question_data.get("rationale", ""),
            source=question_data.get("source_refs", ""),
        )
        if self.provider == "openai" and self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        if self.provider == "groq" and self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        if self.provider == "mistral" and self.mistral_client:
            response = self.mistral_client.chat.complete(
                model=self.model_name or "mistral-small-latest",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        if self.provider == "gemini" and self.gemini_client:
            candidates = list(dict.fromkeys(
                ([self.model_name] if self.model_name else []) + list(self.GEMINI_MODEL_FALLBACKS)
            ))
            for model_name in candidates:
                try:
                    response = self.gemini_client.models.generate_content(model=model_name, contents=prompt)
                    if response and response.text:
                        return response.text
                except Exception:
                    continue
        raise RuntimeError("El proveedor de IA no devolvió orientación.")

    def explain_question(self, question_data: dict) -> str:
        """Provides a socratic and educational explanation for a question."""
        
        # Fetch Normativa Context for Explanation
        normativa_context = ""
        try:
            normativa = NormativaManager()
            normativa_context = normativa.get_law_context(question_data.get('rationale', ''))
        except Exception as e:
            print(
                "DEBUG: Error fetching normativa context for explanation: "
                f"{type(e).__name__}"
            )

        prompt = f"""
        Actúa como tutor de práctica especializado en normativa aplicable a la DIAN. Tu objetivo es explicar la lógica detrás de la siguiente pregunta de práctica sin revelar la respuesta correcta directamente si es posible, o guiando al estudiante a través del razonamiento legal.
        
        {normativa_context}
        
        CASO/SITUACIÓN: {question_data.get('stem')}
        OPCIONES DISPONIBLES: {question_data.get('options_json')}
        RESPUESTA CORRECTA (para tu referencia): {question_data.get('correct_key')}
        JUSTIFICACIÓN TÉCNICA: {question_data.get('rationale')}
        
        INSTRUCCIONES PARA EL TUTOR:
        1. Sé pedagógico y cercano.
        2. Explica la norma o concepto legal involucrado.
        3. Ayuda a descartar las opciones incorrectas basándote en la lógica del caso.
        4. No digas simplemente "La respuesta es A". Di algo como "En este escenario, debemos observar que la norma X indica Y... por lo tanto..."
        5. Mantén la explicación concisa (máximo 2 párrafos).
        
        IDIOMA: ESPAÑOL.
        """
        
        try:
            if self.provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
                
            elif self.provider == "groq" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content

            elif self.provider == "mistral" and self.mistral_client:
                response = self.mistral_client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
                
            elif self.provider == "gemini":
                candidates = list(self.GEMINI_MODEL_FALLBACKS)
                exp_content = ""
                config = types.GenerateContentConfig(
                    safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")]
                )
                for model_name in candidates:
                    try:
                        response = self.gemini_client.models.generate_content(model=model_name, contents=prompt, config=config)
                        if response and response.text:
                            exp_content = response.text
                            break
                    except Exception:
                        continue
                if exp_content:
                    return exp_content
                return "No se pudo obtener una explicación de Gemini v43.0."
                
            return "No se pudo conectar con el proveedor de IA para la explicación."
        except Exception as e:
            # Let's see what model was active
            m_name = getattr(self, "model_name", "Unknown")
            return (
                f"No se pudo obtener la explicación con el modelo [{m_name}] "
                f"({type(e).__name__})."
            )

    def audit_question(self, question_data: dict, source_context: str = "") -> dict:
        """Audit a question against the internal PJS practice rubric using AI."""
        # Fetch Normativa Context for Audit
        normativa_context = source_context.strip()
        try:
            if not normativa_context:
                from core.normativa import NormativaManager
                normativa = NormativaManager()
                normativa_context = normativa.get_law_context(question_data.get('stem', '') + " " + question_data.get('rationale', ''))
        except Exception as e:
            print(
                "DEBUG: Error fetching normativa context for audit: "
                f"{type(e).__name__}"
            )

        prompt = f"""
        Actúa como auditor editorial independiente. Evalúa la pregunta según la metodología PJS descrita en las especificaciones CNSC LP-004-2026 para DIAN 2676; no afirmes representar a la CNSC ni disponer de la GOA aún no publicada.
        
        {normativa_context}
        
        DATOS DE LA PREGUNTA:
        CASO BASE: {question_data.get('case_text', '')}
        TEMA: {question_data.get('topic')}
        ENUNCIADO: {question_data.get('stem')}
        OPCIONES: {question_data.get('options_json')}
        CLAVE: {question_data.get('correct_key')}
        JUSTIFICACIÓN: {question_data.get('rationale')}
        
        CRITERIOS DE EVALUACIÓN (0-10):
        1. Precisión Legal: ¿La clave coincide con la norma citada?
        2. Dependencia Situacional: ¿La clave exige usar uno o más datos concretos del caso y no puede resolverse solo memorizando la norma?
        3. Coherencia Situacional: ¿El caso plantea un escenario laboral realista?
        4. Calidad de Distractores: ¿Son plausibles y técnicos?
        5. No Inducción: ¿La pregunta no regala la respuesta?
        6. Justificación Técnica: ¿Es clara y cita artículos reales?
        
        RESPONDE ÚNICAMENTE EN FORMATO JSON:
        {{
            "score": 0-10,
            "status": "APPROVED | REJECTED | IMPROVABLE",
            "critique": "Breve análisis técnico",
            "findings": ["Hallazgo 1", "Hallazgo 2"],
            "suggestion": "Mejora propuesta"
        }}
        """
        
        try:
            content = ""
            if self.provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
            elif self.provider == "mistral" and self.mistral_client:
                # v47.3 Audit Mistral
                response = self.mistral_client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content

            elif self.provider == "gemini":
                # Prefer a stable production model, with a maintained alias as fallback.
                candidates = list(self.GEMINI_MODEL_FALLBACKS)
                
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    ]
                )
                
                content = ""
                fail_log = []
                for model_name in candidates:
                    try:
                        print(f"DEBUG: Auditing with Gemini ({model_name})... Mikey v44")
                        response = self.gemini_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            content = response.text
                            break
                    except Exception as e:
                        fail_log.append(f"{model_name}: {type(e).__name__}")
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            time.sleep(2) # Cooldown Mikey
                        continue
                
                # Fallback Universal v47.1 (Intento de Rescate de Auditoría)
                if not content:
                    fb_client = getattr(self, 'fallback_client', None)
                    fb_type = getattr(self, 'fallback_type', 'openai')
                    # ``openai_client`` is initialized to None for a Gemini
                    # request.  Checking only ``hasattr`` dereferenced None
                    # here and hid the real Gemini error behind base_url.
                    primary_fallback = getattr(self, "openai_client", None)
                    if not fb_client and primary_fallback is not None:
                        fb_client = primary_fallback
                        base_url = str(getattr(fb_client, "base_url", ""))
                        fb_type = "openai" if "api.openai.com" in base_url else "groq"
                    
                    if fb_client:
                        print(f"⚠️ [v47.1] Gemini Audit Failed. Attempting Fallback Rescue with {fb_type}... Mikey")
                        try:
                            model_fb = "gpt-4o-mini" if fb_type == "openai" else "llama-3.3-70b-versatile"
                            response = fb_client.chat.completions.create(
                                model=model_fb,
                                messages=[{"role": "user", "content": prompt}],
                                response_format={"type": "json_object"}
                            )
                            content = response.choices[0].message.content
                        except Exception as ge:
                            fail_log.append(
                                f"Fallback_Error: {type(ge).__name__}"
                            )
                
                if not content:
                    raise Exception(f"Falla total v47.1 Mikey - Auditoría Inalcanzable: {', '.join(fail_log)}")

                if "```json" in content:
                    content = content.replace("```json", "").split("```")[0].strip()
                elif "```" in content:
                    content = content.replace("```", "").strip()
            
            # v47 JSON Repair Célula Mikey
            res = repair_and_parse_json(content)
            if not res:
                raise Exception("Fallo en auditoría: El JSON del auditor no es válido tras reparación.")
            res["critique"] = f"[v47.1] {res.get('critique', '')}" # Quantum Shield v2 Mikey
            return res
        except Exception as e:
            return {
                "score": 0,
                "status": "ERROR",
                "critique": (
                    "La auditoría IA no pudo completarse "
                    f"({type(e).__name__}). La candidata continúa pendiente."
                ),
            }

    def generate_case_study(self, topic: str, num_questions: int = 3, difficulty: int = 2, source_context: str = "") -> dict:
        """Generate a PJS practice case with one scenario and related questions."""
        
        # Internal practice composition: a functional case shares three items.
        num_questions = 3

        prompt = f"""
        Actúa como editor de material de práctica situacional enfocado en funciones de la DIAN.
        Tu tarea es crear un caso PJS de práctica completo y original. No afirmes representar
        a la DIAN o a la CNSC ni disponer de la GOA aún no publicada.
        
        REGLA CRÍTICA DE CONTEXTO:
        * El entorno de trabajo debe ser EXCLUSIVAMENTE la DIAN.
        * El protagonista es un funcionario de la DIAN.
        * EVITA CUALQUIER MENCIÓN a la CNSC como lugar de trabajo o jefatura.
        
        TEMA PRINCIPAL: {topic}
        DIFICULTAD EDITORIAL INTERNA: {difficulty}/10
        RÚBRICA: 1-2 reconocimiento/comprensión; 3-4 aplicación; 5-6 integración y análisis; 7-8 juicio avanzado; 9-10 transferencia compleja. No la presentes como escala oficial de la CNSC.
        CANTIDAD DE PREGUNTAS: {num_questions}

        FUENTE DE REFERENCIA SUMINISTRADA (su oficialidad y vigencia deben verificarse):
        {source_context or "No se suministró una fuente verificable. Evita detalles jurídicos no sustentados."}

        REGLA DE PRECISIÓN NORMATIVA:
        * Usa exclusivamente hechos jurídicos comprobables en la fuente autorizada.
        * No inventes artículos, plazos, autoridades, actos administrativos ni porcentajes.
        * Si falta sustento, pregunta sobre el procedimiento general que sí consta en la fuente.
        
        ESTRUCTURA DEL CONTENIDO:
        1. TÍTULO: Un título profesional y descriptivo.
        2. TEXTO DEL CASO (SITUACIÓN): Una situación laboral clara y autosuficiente.
           - Debe describir una situación compleja en un entorno de la DIAN (Aduanas, Fiscalización, Atención, etc.).
           - Incluye detalles técnicos, cifras, fechas o normativas implicadas.
           - El protagonista debe enfrentar un dilema o una serie de procedimientos a resolver.
        3. ENUNCIADOS: Genera EXACTAMENTE tres (3) enunciados que SOLO se puedan responder leyendo el mismo caso.
           - Cada pregunta debe indagar sobre una parte específica del procedimiento descrito.
           - La clave debe depender de uno o mÃ¡s datos concretos del caso; si puede responderse sin leerlo, es invÃ¡lida.
           - Evita definiciones, objetos generales de normas y memoria aislada de artÃ­culos.
        
        FORMATO DE SALIDA (JSON ÚNICAMENTE):
        {{
            "title": "Título del Caso",
        FORMATO DE SALIDA (JSON ÚNICAMENTE):
        {{
            "title": "Título del Caso",
            "text": "Narrativa completa del caso...",
            "topic": "{topic}",
            "questions": [
                {{
                    "stem": "Pregunta relacionada con el caso...",
                    "options": {{
                        "A": "Opción 1",
                        "B": "Opción 2",
                        "C": "Opción 3"
                    }},
                    "correct_key": "A",
                    "rationale": "Justificación técnica...",
                    "source_ref": "Fuente oficial que sustenta la clave",
                    "track": "FUNCIONAL",
                    "competency": "Competencia evaluada"
                }}
            ]
        }}
        
        IMPORTANTE: Responde ÚNICAMENTE con el objeto JSON. NO uses bloques de código markdown (```json). SOlo el texto raw del JSON. Si es necesario, escapa las comillas dobles dentro del texto con \".
        """
        
        try:
            content = ""
            if self.provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
            elif self.provider == "gemini":
                model_name = (self.model_name or self.DEFAULT_GEMINI_MODEL).replace("models/", "")
                config = types.GenerateContentConfig(response_mime_type="application/json")
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    content = response.text
                except Exception as ex:
                     # Fallback to text if JSON mode fails
                     response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt + "\nRESPOND ONLY IN JSON."
                    )
                     content = response.text

            elif self.provider == "groq" and self.openai_client:
                 response = self.openai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                 content = response.choices[0].message.content

            elif self.provider == "mistral" and self.mistral_client:
                 response = self.mistral_client.chat.complete(
                    model=self.model_name if self.model_name else "mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                 content = response.choices[0].message.content
                 
            # Parse JSON without writing provider content to application logs.
            data = repair_and_parse_json(content)
            if not data:
                raise ValueError("La respuesta del proveedor no contiene un caso JSON válido.")
                
            return data
            
        except Exception as e:
            print(f"ERROR generating Case Study: {type(e).__name__}")
            raise e

    def optimize_question(self, question_data: dict, audit_report: dict) -> dict:
        """Optimizes a question based on audit findings, rewriting distractors and stem if necessary. Mikey v50"""
        
        prompt = f"""
        Actúa como editor independiente de material de práctica PJS basado en normativa aplicable a la DIAN.
        No afirmes representar a la CNSC ni a la DIAN, y no atribuyas esta plantilla a la GOA.
        Tu misión es corregir, pulir y optimizar la siguiente pregunta de juicio situacional basándote en los hallazgos de una auditoría previa.
        
        DATOS DE LA PREGUNTA ORIGINAL:
        TEMA: {question_data.get('topic')}
        ENUNCIADO ORIGINAL: {question_data.get('stem')}
        OPCIONES ORIGINALES: {question_data.get('options_json')}
        CLAVE ORIGINAL: {question_data.get('correct_key')}
        JUSTIFICACIÓN ORIGINAL: {question_data.get('rationale')}
        
        INFORME DE AUDITORÍA:
        PUNTAJE CALIDAD: {audit_report.get('score')}/10
        CRÍTICA: {audit_report.get('critique')}
        HALLAZGOS: {audit_report.get('findings')}
        SUGERENCIA DE MEJORA: {audit_report.get('suggestion')}
        
        REGLAS PARA LA OPTIMIZACIÓN:
        1. **Plausibilidad de Distractores (CRÍTICO)**: Los distractores (opciones incorrectas) deben ser altamente competitivos, técnicos y plausibles. Evita opciones absurdas, cómicas o fáciles de descartar por sentido común.
        2. **Precisión Normativa**: Asegura que el enunciado de la situación sea coherente con la legislación de la DIAN aplicable (Estatuto Tributario, etc.).
        3. **Conservar la Clave**: Mantén la misma letra clave correcta y el fundamento de ley original, a menos que el auditor haya señalado una discrepancia legal grave en la clave, en cuyo caso corrígela.
        4. **Formato**: Genera una estructura de Juicio Situacional con CASO + PREGUNTA (integrados en el stem), 3 opciones (A, B, C) y justificación rigurosa.
        
        FORMATO DE SALIDA (Objeto JSON obligatorio):
        {{
            "track": "{question_data.get('track', 'FUNCIONAL')}",
            "macro_dominio": "{question_data.get('macro_dominio', 'Transversal')}",
            "micro_competencia": "{question_data.get('micro_competencia', 'General')}",
            "topic": "{question_data.get('topic', 'Tema')}",
            "difficulty": {question_data.get('difficulty', 2)},
            "stem": "SITUACIÓN: [Caso mejorado de 80-120 palabras]. PREGUNTA: [Enunciado mejorado]?",
            "options": {{
                "A": "Opción A mejorada",
                "B": "Opción B mejorada",
                "C": "Opción C mejorada"
            }},
            "correct_key": "Letra correcta",
            "rationale": "Justificación mejorada basada en el artículo exacto."
        }}
        
        IMPORTANTE: No respondas con nada que no sea el JSON solicitado.
        """
        
        try:
            content = ""
            if self.provider == "openai" and self.openai_client:
                model = self.model_name if self.model_name else "gpt-4o-mini"
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Genera exclusivamente JSON válido para optimización de preguntas."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
            elif self.provider == "groq" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Genera exclusivamente JSON válido para optimización de preguntas."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
            elif self.provider == "mistral" and self.mistral_client:
                response = self.mistral_client.chat.complete(
                    model=self.model_name if self.model_name else "mistral-large-latest",
                    messages=[
                        {"role": "system", "content": "Genera exclusivamente JSON válido para optimización de preguntas."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
            elif self.provider == "gemini":
                candidates = list(self.GEMINI_MODEL_FALLBACKS)
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")
                    ]
                )
                
                for model_name in candidates:
                    try:
                        print(f"DEBUG: Optimizing with Gemini ({model_name})... Mikey v50")
                        response = self.gemini_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            content = response.text
                            break
                    except Exception as e:
                        print(
                            f"DEBUG: Error Gemini {model_name}: "
                            f"{type(e).__name__}"
                        )
                        continue
                        
                # Fallback Rescue
                if not content and hasattr(self, 'fallback_client') and self.fallback_client:
                    fb_t = getattr(self, 'fallback_type', 'openai')
                    print(f"⚠️ Gemini optimization failed. Activating Rescue with {fb_t}... Mikey")
                    try:
                        fb_model = "gpt-4o-mini" if fb_t == "openai" else "llama-3.3-70b-versatile"
                        fb_response = self.fallback_client.chat.completions.create(
                            model=fb_model,
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"}
                        )
                        content = fb_response.choices[0].message.content
                    except Exception as fe:
                        print(f"❌ Rescue failed: {type(fe).__name__}")
            
            if not content:
                raise Exception("La IA no devolvió contenido para la optimización.")
                
            if "```json" in content:
                content = content.replace("```json", "").split("```")[0].strip()
            elif "```" in content:
                content = content.replace("```", "").strip()
                
            data = repair_and_parse_json(content)
            if not data:
                raise Exception("Fallo en optimización: El JSON retornado no es válido tras reparación.")
                
            return data
            
        except Exception as e:
            print(f"ERROR optimizing question: {type(e).__name__}")
            raise e

