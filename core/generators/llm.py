import os
import json
import uuid
import datetime
import time
from typing import List
from db.models import Question
from core.dedupe import compute_hash
import openai
import google.generativeai as genai
from core.normativa import NormativaManager

class LLMGenerator:
    def __init__(self, provider: str, api_key: str, model_name: str = None):
        self.provider = provider.lower()
        self.api_key = api_key.strip() if api_key else ""
        self.model_name = model_name
        
        # Try to initialize both if possible (for fallbacks)
        self.openai_client = None
        if self.provider == "openai" and self.api_key:
            self.openai_client = openai.OpenAI(api_key=self.api_key)
        
        if self.provider == "gemini" and self.api_key:
            genai.configure(api_key=self.api_key)
            
        if self.provider == "groq" and self.api_key:
            self.openai_client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            
    def generate_from_text(self, text: str, count: int = 5, difficulty: int = 2) -> List[dict]:
        """Generates questions by splitting into smaller chunks for reliability."""
        all_results = []
        batch_size = 5 # Reliable size for JSON generation
        
        remaining = count
        while remaining > 0:
            current_batch = min(remaining, batch_size)
            print(f"DEBUG: Generating batch of {current_batch} questions (Remaining: {remaining})...")
            try:
                batch_results = self._generate_batch(text, current_batch, difficulty)
                all_results.extend(batch_results)
                remaining -= current_batch
                # Small delay to avoid aggressive rate limits in some providers
                if remaining > 0:
                    time.sleep(1)
            except Exception as e:
                # If we have some results already, return them instead of failing completely
                if all_results:
                    print(f"WARNING: Generation interrupted, but returning {len(all_results)} questions already generated. Error: {e}")
                    break
                else:
                    raise e
                    
        return all_results

    def _generate_batch(self, text: str, count: int = 5, difficulty: int = 2) -> List[dict]:
        # Fetch OPEC context if available
        opec_context = ""
        try:
            from db.session import SessionLocal
            from db.models import UserOPEC
            db = SessionLocal()
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

        # Increase context window to 10000 characters for better results
        context = text[:10000]
        
        prompt = f"""
        Actúa como un Experto Constructor de Ítems de la CNSC para los procesos de selección de la DIAN.
        Tu misión es generar EXACTAMENTE {count} preguntas de selección múltiple con un nivel de DIFICULTAD: {difficulty} (1=Básico, 2=Intermedio, 3=Avanzado).
        {opec_context}
        {normativa_context}
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

        TEXTO DE REFERENCIA (Inyecta este contenido en los casos):
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
                
            elif self.provider == "gemini":
                # Modelos verificados mediante diagnóstico en la cuenta del usuario
                candidates = [
                    "models/gemini-flash-latest",
                    "models/gemini-2.0-flash-001",
                    "models/gemini-pro-latest",
                    "models/gemini-1.5-pro-latest",
                    "models/gemini-2.0-flash-lite-001",
                    "gemini-pro"
                ]
                # If specialized model requested, put it at the very beginning
                if self.model_name and "gemini-1.5-flash" not in self.model_name:
                    clean_name = self.model_name.replace("models/", "")
                    full_name = f"models/{clean_name}"
                    if full_name in candidates:
                        candidates.remove(full_name)
                    candidates.insert(0, full_name)
                
                content = ""
                last_error = None
                
                # Relax security filters for technical legal content
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                for model_name in candidates:
                    try:
                        print(f"DEBUG: Enviando lote a Gemini ({model_name})...")
                        model = genai.GenerativeModel(model_name=model_name)
                        response = model.generate_content(prompt, safety_settings=safety_settings)
                        if response and response.text:
                            content = response.text
                            break
                    except Exception as e:
                        last_error = e
                        err_str = str(e).lower()
                        if "404" in err_str:
                             print(f"⚠️ El modelo {model_name} no está disponible, intentando siguiente...")
                             continue
                        if "safety" in err_str:
                             print(f"⚠️ Aviso: Gemini bloqueó contenido por seguridad en {model_name}.")
                        print(f"DEBUG: Fallo Gemini {model_name}: {e}")
                        continue
                
                if not content:
                    if "quota" in str(last_error).lower() or "429" in str(last_error):
                        raise Exception("❌ Cuota de Gemini agotada (Límite por minuto). Prueba de nuevo en 60 segundos o usa Groq.")
                    raise Exception(f"Gemini falló: {last_error}")

                # Cleanup markdown
                if "```json" in content:
                    content = content.replace("```json", "").split("```")[0]
                elif "```" in content:
                    content = content.replace("```", "")
        
            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # Attempt to clean common errors
                content = content.replace("'", '"') # risky but common Fix
                try:
                    data = json.loads(content)
                except:
                    raise Exception(f"Error de sintaxis JSON en el lote: {str(e)}")

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
                
            elif self.provider == "gemini":
                candidates = [
                    "models/gemini-flash-latest",
                    "models/gemini-2.0-flash-001",
                    "models/gemini-pro-latest",
                    "models/gemini-1.5-pro-latest",
                    "models/gemini-2.0-flash-lite-001",
                    "gemini-pro"
                ]
                
                # Priority to user selected model. Mikey
                if self.model_name and "gemini-1.5-flash" not in self.model_name:
                    clean_name = self.model_name.replace("models/", "")
                    full_name = f"models/{clean_name}"
                    if full_name in candidates: candidates.remove(full_name)
                    candidates.insert(0, full_name)
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                exp_content = ""
                for model_name in candidates:
                    try:
                        model = genai.GenerativeModel(model_name=model_name)
                        response = model.generate_content(prompt, safety_settings=safety_settings)
                        if response and response.text:
                            exp_content = response.text
                            break
                    except Exception:
                        continue
                
                if exp_content:
                    return exp_content
                return "No se pudo obtener una explicación de los modelos de Gemini disponibles."
                
            return "No se pudo conectar con el proveedor de IA para la explicación."
        except Exception as e:
            # Let's see what model was active
            m_name = getattr(self, "model_name", "Unknown")
            return f"Tutor Mikey Error con modelo [{m_name}]: {str(e)}"


