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


class LLMGenerator:
    def __init__(self, provider: str, api_key: str, model_name: str = None, goa_mode: bool = True):
        self.provider = provider.lower()
        self.api_key = api_key.strip() if api_key else ""
        self.model_name = model_name
        self.goa_mode = goa_mode
        
        # Try to initialize both if possible (for fallbacks)
        self.openai_client = None
        self.gemini_client = None
        self.mistral_client = None

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
                print(f"ERROR: Batch {i} failed: {e}")
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
            print(f"DEBUG: Error fetching OPEC context: {e}")

        # Fetch Normativa Context (RAG Phase 4)
        normativa_context = ""
        try:
            normativa = NormativaManager()
            # Use topic or text preview as query
            normativa_context = normativa.get_law_context(text[:500])
        except Exception as e:
            print(f"DEBUG: Error fetching normativa context: {e}")

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
            print(f"DEBUG: Error loading Res 65 context: {e}")

        # GOA logic v46 Mikey
        goa_instr = ""
        if self.goa_mode:
            goa_instr = """
        REQUISITOS METODOLÓGICOS (Protocolo GOA 2667 - Estándar CNSC):
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
        Actúa como un Experto en Normativa de la DIAN y Constructor de Preguntas.
        Tu misión es generar EXACTAMENTE {count} preguntas de selección múltiple con un nivel de DIFICULTAD: {difficulty} (1=Básico, 2=Intermedio, 3=Avanzado).
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
              "track": "FUNCIONAL | COMPORTAMENTAL | INTEGRIDAD",
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
                            {"role": "system", "content": "Actúa como un experto en DIAN. Genera exclusivamente JSON válido."},
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
                candidates = [
                    "gemini-2.0-flash-exp",
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-001",
                    "gemini-1.5-flash-002",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro-002",
                    "gemini-1.5-pro"
                ]
                
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
                            # v47.2 Adaptive Backoff: Try to extract retry-after
                            wait_time = 10 # Safer default for peak hours
                            if "retry in " in err_str:
                                try:
                                    # Extract number after "retry in "
                                    parts = err_str.split("retry in ")
                                    wait_time = float(parts[1].split("s")[0]) + 1
                                except: pass
                            print(f"⚠️ [429] Cuota excedida en {model_name}. Esperando {wait_time}s para reintento automático... Mikey v6.2")
                            time.sleep(wait_time) 
                            # Re-attempt same model once before switching
                            try:
                                response = self.gemini_client.models.generate_content(
                                    model=model_name,
                                    contents=prompt,
                                    config=config
                                )
                                if response and response.text:
                                    content = response.text
                                    break
                            except: pass
                        
                        print(f"DEBUG: Fallo Gemini {model_name}: {e}")
                        continue
                
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
                        print(f"❌ Falló incluso el rescate {fb_t}: {fe}")

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
                else:
                    raise Exception(f"Límite de velocidad (Rate Limit) alcanzado: {error_msg}")
            raise Exception(f"Fallo en lote: {error_msg}")

    def explain_question(self, question_data: dict) -> str:
        """Provides a socratic and educational explanation for a question."""
        
        # Fetch Normativa Context for Explanation
        normativa_context = ""
        try:
            normativa = NormativaManager()
            normativa_context = normativa.get_law_context(question_data.get('rationale', ''))
        except Exception as e:
            print(f"DEBUG: Error fetching normativa context for explanation: {e}")

        prompt = f"""
        Actúa como un Tutor Experto de la DIAN. Tu objetivo es explicar la lógica detrás de la siguiente pregunta de examen sin revelar la respuesta correcta directamente si es posible, o guiando al estudiante a través del razonamiento legal.
        
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
                candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
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
            return f"Tutor Mikey Error con modelo [{m_name}]: {str(e)}"

    def audit_question(self, question_data: dict) -> dict:
        """Audits a question against CNSC quality standards using IA. Mikey"""
        # Fetch Normativa Context for Audit
        normativa_context = ""
        try:
            from core.normativa import NormativaManager
            normativa = NormativaManager()
            normativa_context = normativa.get_law_context(question_data.get('stem', '') + " " + question_data.get('rationale', ''))
        except Exception as e:
            print(f"DEBUG: Error fetching normativa context for audit: {e}")

        prompt = f"""
        Actúa como un Auditor de Calidad Senior de la CNSC. Evalúa la siguiente pregunta bajo el Protocolo 2667 para la DIAN.
        
        {normativa_context}
        
        DATOS DE LA PREGUNTA:
        TEMA: {question_data.get('topic')}
        ENUNCIADO: {question_data.get('stem')}
        OPCIONES: {question_data.get('options_json')}
        CLAVE: {question_data.get('correct_key')}
        JUSTIFICACIÓN: {question_data.get('rationale')}
        
        CRITERIOS DE EVALUACIÓN (0-10):
        1. Precisión Legal: ¿La clave coincide con la norma citada?
        2. Coherencia Situacional: ¿El caso plantea un escenario laboral realista?
        3. Calidad de Distractores: ¿Son plausibles y técnicos?
        4. No Inducción: ¿La pregunta no regala la respuesta?
        5. Justificación Técnica: ¿Es clara y cita artículos reales?
        
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
                # v43 Mikey: Resiliency List with new SDK
                candidates = [
                    "gemini-2.0-flash",
                    "gemini-1.5-flash",
                    "gemini-2.0-flash-001",
                    "gemini-pro",
                    "gemini-1.5-pro"
                ]
                
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
                        fail_log.append(f"{model_name}: {str(e)[:40]}")
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            time.sleep(2) # Cooldown Mikey
                        continue
                
                # Fallback Universal v47.1 (Intento de Rescate de Auditoría)
                if not content:
                    fb_client = getattr(self, 'fallback_client', None)
                    fb_type = getattr(self, 'fallback_type', 'openai')
                    if not fb_client and hasattr(self, 'openai_client'): 
                        fb_client = self.openai_client
                        fb_type = "openai" if "api.openai.com" in str(fb_client.base_url) else "groq"
                    
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
                            fail_log.append(f"Fallback_Error: {str(ge)[:40]}")
                
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
            return {"score": 0, "status": "ERROR", "critique": f"Error en auditoría (v45.0 Mikey): {e}"}
