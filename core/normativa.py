import os
import re
import hashlib
import json
from rapidfuzz import process, fuzz
from db.session import SessionLocal
from db.models import NormativaChunk
from core.ai.usage_policy import AIUsageLimitError, reserve_ai_usage
from core.safe_uploads import UnsafeUpload, extract_pdf_pages


MAX_EMBEDDINGS_PER_RUN = 50

def cosine_similarity(v1, v2):
    """Calcula la similitud de coseno entre dos vectores."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(a * a for a in v2) ** 0.5
    if not norm_v1 or not norm_v2:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

class NormativaManager:
    def __init__(self, folder_path="data/normativa"):
        self.folder_path = folder_path

    def _get_embedding(
        self,
        text: str,
        *,
        user_id: int | None = None,
        task_type: str = "normativa_embedding",
    ) -> list | None:
        """Genera el embedding de un fragmento de texto usando Gemini."""
        from core.config import get_api_key
        from google import genai
        
        api_key = get_api_key("gemini")
        if not api_key:
            return None
            
        reservation = None
        try:
            reservation = reserve_ai_usage(
                SessionLocal,
                user_id=user_id,
                provider="gemini",
                model="gemini-embedding-2",
                task_type=task_type,
                prompt=text,
                planned_calls=1,
                prompt_version="normativa-embedding-v1",
            )
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text
            )
            if response and response.embeddings:
                reservation.finish(success=True)
                return response.embeddings[0].values
            reservation.finish(success=False, error=RuntimeError("empty_embedding"))
        except AIUsageLimitError:
            raise
        except Exception as exc:
            if reservation is not None:
                reservation.finish(success=False, error=exc)
            print(f"Error generando embedding con Gemini: {type(exc).__name__}")
        return None

    def backfill_embeddings(
        self,
        progress_callback=None,
        *,
        limit: int = MAX_EMBEDDINGS_PER_RUN,
        user_id: int | None = None,
    ) -> int:
        """Calcula un lote acotado de embeddings para fragmentos pendientes."""
        safe_limit = max(1, min(int(limit), MAX_EMBEDDINGS_PER_RUN))
        db = SessionLocal()
        try:
            chunks = (
                db.query(NormativaChunk)
                .filter(NormativaChunk.embedding_json.is_(None))
                .order_by(NormativaChunk.id.asc())
                .limit(safe_limit)
                .all()
            )
            total = len(chunks)
            updated_count = 0
            
            for idx, chunk in enumerate(chunks):
                if progress_callback:
                    progress_callback(int(((idx + 1) / total) * 100), f"Procesando vector {idx+1} de {total}...")
                    
                vector = self._get_embedding(
                    chunk.content,
                    user_id=user_id,
                    task_type="normativa_backfill_embedding",
                )
                if vector:
                    chunk.embedding_json = json.dumps(vector)
                    updated_count += 1
                    # Guardar progresivamente cada 10 registros
                    if updated_count % 10 == 0:
                        db.commit()
            
            db.commit()
            return updated_count
        finally:
            db.close()

    def index_all(self, progress_callback=None):
        """
        Lee todos los PDFs, los divide en fragmentos con solapamiento y los guarda en la BD.
        Evita duplicados mediante hash. v50.0 Mikey (Vectorial)
        """
        if not os.path.exists(self.folder_path):
            return 0

        db = SessionLocal()
        indexed_count = 0
        
        pdf_files = [f for f in os.listdir(self.folder_path) if f.endswith(".pdf")]
        total_files = len(pdf_files)

        try:
            for idx, file in enumerate(pdf_files):
                if progress_callback:
                    progress_callback(
                        int((idx / max(total_files, 1)) * 100), f"Indexando {file}..."
                    )

                full_path = os.path.join(self.folder_path, file)
                try:
                    with open(full_path, "rb") as handle:
                        page_texts = extract_pdf_pages(handle.read())
                    for page_number, text in enumerate(page_texts, start=1):
                        if not text or len(text.strip()) < 50:
                            continue

                        # Dividir página en fragmentos de ~1000 con 200 de solapamiento.
                        # Los vectores se generan después, en un lote con límite explícito.
                        chunk_size = 1000
                        overlap = 200
                        for start in range(0, len(text), chunk_size - overlap):
                            chunk_text = text[start:start + chunk_size]
                            h = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                            legacy_h = hashlib.md5(
                                chunk_text.encode("utf-8"), usedforsecurity=False
                            ).hexdigest()
                            exists = (
                                db.query(NormativaChunk)
                                .filter(NormativaChunk.hash_content.in_([h, legacy_h]))
                                .first()
                            )
                            if not exists:
                                db.add(
                                    NormativaChunk(
                                        source_file=file,
                                        page=page_number,
                                        content=chunk_text,
                                        hash_content=h,
                                        embedding_json=None,
                                    )
                                )
                                indexed_count += 1
                    db.commit()
                except UnsafeUpload as exc:
                    db.rollback()
                    print(f"PDF omitido: {type(exc).__name__}")
                except Exception as exc:
                    db.rollback()
                    print(f"Error indexando PDF: {type(exc).__name__}")
            return indexed_count
        finally:
            db.close()

    def search_in_laws(self, query, limit=5):
        """
        Busca en la BD usando embeddings vectoriales por similitud de coseno.
        Si falla o no hay datos vectoriales, usa el fallback léxico tradicional.
        """
        db = SessionLocal()
        try:
            # 1. Intentar búsqueda semántica con embeddings
            try:
                query_vector = self._get_embedding(query)
            except AIUsageLimitError:
                # Searching the local legal library must remain available even
                # after the provider budget is exhausted.
                query_vector = None
            if query_vector:
                # Consultar chunks que tengan embedding
                candidates = db.query(NormativaChunk).filter(NormativaChunk.embedding_json.isnot(None)).all()
                if candidates:
                    scored = []
                    for c in candidates:
                        try:
                            c_vector = json.loads(c.embedding_json)
                            score = cosine_similarity(query_vector, c_vector)
                            scored.append((c, score * 100.0))  # Escalar a 0-100 para consistencia
                        except Exception:
                            continue
                    
                    if scored:
                        scored.sort(key=lambda x: x[1], reverse=True)
                        top_results = scored[:limit]
                        
                        results = []
                        for c, score in top_results:
                            results.append({
                                "source": c.source_file,
                                "page": c.page,
                                "snippet": c.content,
                                "score": score
                            })
                        print(f"DEBUG RAG: Búsqueda Semántica exitosa ({len(results)} resultados)")
                        return results

            # 2. FALLBACK: Búsqueda rápida por palabras clave (SQL + RapidFuzz)
            print("DEBUG RAG: Activado Fallback Léxico (ilike + rapidfuzz)")
            words = [w.lower() for w in re.findall(r'\b\w+\b', query) if len(w) > 3]
            if not words:
                return []
            
            base_query = db.query(NormativaChunk)
            filters = [NormativaChunk.content.ilike(f"%{w}%") for w in words]
            from sqlalchemy import or_
            candidates = base_query.filter(or_(*filters)).limit(50).all()
            
            if not candidates:
                return []

            scored = []
            for c in candidates:
                score = fuzz.partial_token_set_ratio(query, c.content)
                scored.append((c, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            top_results = scored[:limit]

            results = []
            for c, score in top_results:
                results.append({
                    "source": c.source_file,
                    "page": c.page,
                    "snippet": c.content,
                    "score": score
                })
            return results
        finally:
            db.close()

    def get_law_context(self, topic):
        """
        Obtiene contexto legal optimizado. Mikey v50 (Híbrido)
        """
        db = SessionLocal()
        count = db.query(NormativaChunk).count()
        db.close()
        
        if count == 0:
            print("⚠️ RAG: Banco vacío. Saltando contexto legal para evitar bloqueo UI.")
            return ""

        snippets = self.search_in_laws(topic)
        if not snippets:
            return ""
        
        context = "\n\n--- REFERENCIAS LEGALES REALES (RAG Vectorial v50) ---\n"
        for s in snippets:
            context += f"Fuente: {s['source']} (Pág. {s['page']} | Score: {int(s['score'])})\n{s['snippet']}\n"
        return context

