import os
import pypdf
import re
import hashlib
from rapidfuzz import process, fuzz
from db.session import SessionLocal
from db.models import NormativaChunk

class NormativaManager:
    def __init__(self, folder_path="data/normativa"):
        self.folder_path = folder_path

    def index_all(self, progress_callback=None):
        """
        Lee todos los PDFs, los divide en fragmentos con solapamiento y los guarda en la BD.
        Evita duplicados mediante hash. v48.0 Mikey
        """
        if not os.path.exists(self.folder_path):
            return 0

        db = SessionLocal()
        indexed_count = 0
        
        pdf_files = [f for f in os.listdir(self.folder_path) if f.endswith(".pdf")]
        total_files = len(pdf_files)

        for idx, file in enumerate(pdf_files):
            if progress_callback:
                progress_callback(int((idx / total_files) * 100), f"Indexando {file}...")
                
            full_path = os.path.join(self.folder_path, file)
            try:
                reader = pypdf.PdfReader(full_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text or len(text.strip()) < 50:
                        continue

                    # Dividir página en fragmentos de ~1000 con 200 de solapamiento
                    chunk_size = 1000
                    overlap = 200
                    for start in range(0, len(text), chunk_size - overlap):
                        end = start + chunk_size
                        chunk_text = text[start:end]
                        
                        h = hashlib.md5(chunk_text.encode()).hexdigest()
                        
                        # Guardar si no existe
                        exists = db.query(NormativaChunk).filter_by(hash_content=h).first()
                        if not exists:
                            new_chunk = NormativaChunk(
                                source_file=file,
                                page=i + 1,
                                content=chunk_text,
                                hash_content=h
                            )
                            db.add(new_chunk)
                            indexed_count += 1
                db.commit()
            except Exception as e:
                print(f"Error indexando {file}: {e}")
        
        db.close()
        return indexed_count

    def search_in_laws(self, query, limit=5):
        """
        Busca en la BD usando palabras clave y ranking de RapidFuzz. Mikey v48
        """
        db = SessionLocal()
        try:
            # 1. Búsqueda rápida por palabras clave (SQL)
            words = [w.lower() for w in re.findall(r'\b\w+\b', query) if len(w) > 3]
            if not words:
                return []
            
            # Buscamos chunks que contengan al menos una palabra clave
            # (En un sistema real usaríamos FTS, aquí simulamos con LIKE para SQLite/Postgres básico)
            base_query = db.query(NormativaChunk)
            filters = [NormativaChunk.content.ilike(f"%{w}%") for w in words]
            # Combinamos con OR para ampliar resultados iniciales
            from sqlalchemy import or_
            candidates = base_query.filter(or_(*filters)).limit(50).all()
            
            if not candidates:
                return []

            # 2. Ranking con RapidFuzz
            scored = []
            for c in candidates:
                score = fuzz.partial_token_set_ratio(query, c.content)
                scored.append((c, score))
            
            # Ordenar por score y limitar
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
        Obtiene contexto legal optimizado. Mikey v48
        """
        # Asegurar indexación básica si la BD está vacía (esto es un fallback)
        db = SessionLocal()
        count = db.query(NormativaChunk).count()
        db.close()
        
        if count == 0:
            print("💡 RAG: Banco vacío, auto-indexando normativa... Mikey v48")
            self.index_all()

        snippets = self.search_in_laws(topic)
        if not snippets:
            return ""
        
        context = "\n\n--- REFERENCIAS LEGALES REALES (RAG Inteligente v48) ---\n"
        for s in snippets:
            context += f"Fuente: {s['source']} (Pág. {s['page']} | Score: {int(s['score'])})\n{s['snippet']}\n"
        return context
