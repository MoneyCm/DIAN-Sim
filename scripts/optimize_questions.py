import os
import sys
import io

# Forzar codificación UTF-8 en consolas de Windows para evitar UnicodeEncodeError al imprimir emojis
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except Exception:
    pass

import argparse
import datetime
import json
from sqlalchemy import text

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal, engine
from db.models import Question
from core.config import get_api_key
from core.generators.llm import LLMGenerator

def log(msg, to_file=True):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    if to_file:
        with open("question_optimization.log", "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

def main():
    parser = argparse.ArgumentParser(description="Audita y optimiza el banco de preguntas del simulador.")
    parser.add_argument("--limit", type=int, default=20, help="Límite máximo de preguntas a procesar en esta ejecución.")
    parser.add_argument("--dry-run", action="store_true", help="Simula el proceso y muestra los resultados en consola sin modificar la base de datos.")
    args = parser.parse_args()

    log(f"🚀 Iniciando proceso de auditoría y optimización (Límite: {args.limit} | Dry-run: {args.dry_run})")

    # 1. Detectar Proveedor de IA
    provider = os.getenv("DEFAULT_PROVIDER", "gemini").lower()
    api_key = get_api_key(provider)

    if not api_key:
        # Fallback de búsqueda a otros proveedores
        for p in ["gemini", "mistral", "openai", "groq"]:
            key = get_api_key(p)
            if key:
                provider = p
                api_key = key
                break

    if not api_key:
        log("❌ Error crítico: No se encontró ninguna API Key configurada para los proveedores (Gemini, Mistral, OpenAI, Groq).")
        return

    log(f"🤖 Utilizando proveedor de IA: {provider.upper()}")
    
    # Configurar modelo adecuado por defecto
    model_name = None
    if provider == "gemini":
        model_name = "gemini-2.0-flash"
    elif provider == "mistral":
        model_name = "mistral-large-latest"
    elif provider == "openai":
        model_name = "gpt-4o-mini"

    generator = LLMGenerator(provider, api_key, model_name=model_name)
    db = SessionLocal()

    try:
        # 2. Consultar preguntas no verificadas
        # Se priorizan las que tienen menor cantidad de éxitos/fallos o sin reportes
        log("🔍 Consultando preguntas candidatas en la base de datos...")
        questions = db.query(Question).filter(
            (Question.is_verified == False) | (Question.quality_report == None)
        ).limit(args.limit).all()

        total_found = len(questions)
        log(f"📋 Se encontraron {total_found} preguntas candidatas para procesar.")

        if total_found == 0:
            log("🎉 ¡El banco de preguntas ya está completamente verificado!")
            return

        processed = 0
        approved = 0
        optimized = 0
        errors = 0

        for i, q in enumerate(questions):
            log(f"\n───────────────────────────────────────────────")
            log(f"📦 [{i+1}/{total_found}] Procesando Pregunta ID: {q.question_id}")
            log(f"Eje/Tema: {q.track} | {q.competency} | {q.topic}")
            log(f"Enunciado: {q.stem[:120]}...")

            q_data = {
                "question_id": q.question_id,
                "track": q.track,
                "macro_dominio": q.macro_dominio,
                "micro_competencia": q.micro_competencia,
                "topic": q.topic,
                "difficulty": q.difficulty,
                "stem": q.stem,
                "options_json": q.options_json,
                "correct_key": q.correct_key,
                "rationale": q.rationale
            }

            try:
                # 3. Ejecutar Auditoría por IA
                log("   🔍 Auditando pregunta...")
                report = generator.audit_question(q_data)
                
                if report.get("status") == "ERROR":
                    log(f"   ❌ Error al auditar: {report.get('critique')}")
                    errors += 1
                    continue

                score = report.get("score", 0)
                status = report.get("status", "REJECTED")
                log(f"   ⭐ Puntaje de calidad: {score}/10 | Estado: {status}")
                log(f"   💬 Crítica: {report.get('critique')}")

                # 4. Decidir acción basada en la calidad
                if score >= 8 and status == "APPROVED":
                    log("   ✅ Pregunta aprobada sin cambios.")
                    approved += 1
                    
                    if not args.dry_run:
                        q.is_verified = True
                        q.quality_report = report
                        db.commit()
                        log("   💾 Cambios guardados en base de datos.")
                else:
                    log("   🔧 Pregunta por debajo de estándares. Iniciando optimización...")
                    
                    # 5. Ejecutar Optimización por IA
                    optimized_q = generator.optimize_question(q_data, report)
                    
                    log(f"   📝 Comparación de Enunciados:")
                    log(f"      [Original]: {q.stem[:120]}...")
                    log(f"      [Optimizado]: {optimized_q.get('stem')[:120]}...")
                    
                    log(f"   📝 Comparación de Opciones:")
                    log(f"      [Original]: {q.options_json}")
                    log(f"      [Optimizado]: {optimized_q.get('options')}")
                    
                    optimized += 1

                    if not args.dry_run:
                        # Reemplazar con los campos mejorados
                        q.stem = optimized_q.get("stem", q.stem)
                        q.options_json = optimized_q.get("options", q.options_json)
                        q.correct_key = optimized_q.get("correct_key", q.correct_key)
                        q.rationale = optimized_q.get("rationale", q.rationale)
                        q.track = optimized_q.get("track", q.track)
                        q.macro_dominio = optimized_q.get("macro_dominio", q.macro_dominio)
                        q.micro_competencia = optimized_q.get("micro_competencia", q.micro_competencia)
                        q.is_verified = True
                        q.quality_report = report
                        
                        db.commit()
                        log("   💾 Pregunta optimizada guardada exitosamente en la base de datos.")

                processed += 1

            except Exception as e:
                db.rollback()
                log(f"   ❌ Error procesando pregunta: {e}")
                errors += 1
                # Si es un error de rate limit (429), detenemos el script de forma segura
                if "429" in str(e) or "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                    log("⚠️ Límite de cuota o rate limit alcanzado. Deteniendo procesamiento por lotes para evitar bloqueos.")
                    break

        log(f"\n───────────────────────────────────────────────")
        log(f"🏁 Lote procesado. Resumen:")
        log(f"   - Candidatas procesadas: {processed}/{total_found}")
        log(f"   - Aprobadas directamente: {approved}")
        log(f"   - Optimizadas / Pulidas: {optimized}")
        log(f"   - Errores en procesamiento: {errors}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
