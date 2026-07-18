# Plan de Implementación: Búsqueda Semántica RAG con Embeddings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar búsqueda semántica por similitud de coseno sobre embeddings de Gemini (`text-embedding-004`) en el módulo RAG de normativa, asegurando migración automática y fallback léxico resiliente.

**Architecture:** Almacenar vectores serializados como JSON en la base de datos (`embedding_json` en `NormativaChunk`). Realizar el cálculo de similitud de coseno en memoria en Python puro para total portabilidad e independencia de extensiones de BD.

**Tech Stack:** Python 3.13, SQLAlchemy, google-genai SDK, SQLite / PostgreSQL.

## Global Constraints
* No requerir la compilación o instalación de extensiones de C externas en la base de datos (como pgvector).
* Mantener compatibilidad absoluta y fallback automático al motor de búsqueda léxica original en caso de falta de conexión o claves.
* Las API keys deben obtenerse usando la función central `get_api_key("gemini")`.

---

### Task 1: Modificar Modelos y Sincronización de Base de Datos

**Files:**
* Modify: [db/models.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/db/models.py)
* Modify: [db/session.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/db/session.py)
* Create: [tests/test_db_migration.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/tests/test_db_migration.py)

**Interfaces:**
* Produces: Columna `embedding_json` disponible en la tabla `normativa_chunks`.

- [ ] **Step 1: Escribir el test que falla para verificar la migración**
  Crear el archivo `tests/test_db_migration.py` con el siguiente código:
  ```python
  import os
  import sys
  PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
  if PROJECT_ROOT not in sys.path:
      sys.path.insert(0, PROJECT_ROOT)

  from db.session import engine
  from sqlalchemy import inspect

  def test_column_exists():
      inspector = inspect(engine)
      columns = [c["name"] for c in inspector.get_columns("normativa_chunks")]
      assert "embedding_json" in columns, "La columna embedding_json debe estar en normativa_chunks"
      print("Prueba de migracion de columna exitosa.")

  if __name__ == "__main__":
      test_column_exists()
  ```

- [ ] **Step 2: Ejecutar el test para verificar que falla**
  Run: `python tests/test_db_migration.py`
  Expected: FAIL con `AssertionError: La columna embedding_json debe estar en normativa_chunks`

- [ ] **Step 3: Modificar `db/models.py`**
  Añadir el campo `embedding_json` a la clase `NormativaChunk` (aproximadamente en la línea 191).
  ```python
      content: Mapped[str] = mapped_column(Text)
      hash_content: Mapped[str] = mapped_column(String, unique=True)
      embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # NUEVA
      created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
  ```

- [ ] **Step 4: Modificar `db/session.py`**
  Modificar el diccionario `new_cols_map` en `db/session.py` (aproximadamente en la línea 90) para incluir la nueva columna en la tabla `normativa_chunks`:
  ```python
          new_cols_map = {
              "normativa_chunks": [("embedding_json", "TEXT")],
              "questions": [("macro_dominio", "VARCHAR"), ...],
  ```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**
  Run: `python tests/test_db_migration.py`
  Expected: PASS con el mensaje `Prueba de migracion de columna exitosa.`

- [ ] **Step 6: Commit**
  ```bash
  git add db/models.py db/session.py tests/test_db_migration.py
  git commit -m "feat: add embedding_json column to normativa_chunks and dynamic migration"
  ```

---

### Task 2: Implementar la Lógica RAG Semántica en `core/normativa.py`

**Files:**
* Modify: [core/normativa.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/core/normativa.py)
* Create: [tests/test_rag_embeddings.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/tests/test_rag_embeddings.py)

**Interfaces:**
* Produces: `NormativaManager.backfill_embeddings() -> int`
* Produces: `NormativaManager.search_in_laws(query) -> list` con soporte vectorial semántico.

- [ ] **Step 1: Escribir el test unitario para verificar búsqueda vectorial y fallback**
  Crear el archivo `tests/test_rag_embeddings.py` con el siguiente código:
  ```python
  import os
  import sys
  PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
  if PROJECT_ROOT not in sys.path:
      sys.path.insert(0, PROJECT_ROOT)

  from core.normativa import NormativaManager
  import json

  def test_cosine_similarity():
      # Simular cálculo matemático en modulo de normativa
      from core.normativa import cosine_similarity
      v1 = [1.0, 0.0, 0.0]
      v2 = [1.0, 0.0, 0.0]
      v3 = [0.0, 1.0, 0.0]
      assert cosine_similarity(v1, v2) == 1.0
      assert cosine_similarity(v1, v3) == 0.0
      print("Prueba de similitud de coseno exitosa.")

  def test_search_fallback():
      manager = NormativaManager()
      # Probar que la busqueda no lance excepciones aunque no haya embeddings o llaves
      results = manager.search_in_laws("impuesto de renta")
      assert isinstance(results, list), "El resultado de la busqueda debe ser una lista"
      print("Prueba de fallback exitosa.")

  if __name__ == "__main__":
      test_cosine_similarity()
      test_search_fallback()
  ```

- [ ] **Step 2: Ejecutar el test para verificar que falla**
  Run: `python tests/test_rag_embeddings.py`
  Expected: FAIL con `ImportError: cannot import name 'cosine_similarity' from 'core.normativa'`

- [ ] **Step 3: Modificar `core/normativa.py`**
  Implementar la función `cosine_similarity`, el método privado `_get_embedding`, el backfill de vectores y actualizar `search_in_laws` e `index_all`.
  
  Añadir el import de `json` en `core/normativa.py` al principio.
  Añadir la función `cosine_similarity` fuera de la clase:
  ```python
  def cosine_similarity(v1, v2):
      dot_product = sum(a * b for a, b in zip(v1, v2))
      norm_v1 = sum(a * a for a in v1) ** 0.5
      norm_v2 = sum(a * a for a in v2) ** 0.5
      if not norm_v1 or not norm_v2:
          return 0.0
      return dot_product / (norm_v1 * norm_v2)
  ```
  
  Agregar los siguientes métodos a `NormativaManager`:
  ```python
      def _get_embedding(self, text: str) -> list:
          """Genera el embedding de un fragmento de texto usando Gemini."""
          from core.config import get_api_key
          from google import genai
          
          api_key = get_api_key("gemini")
          if not api_key:
              return None
              
          try:
              client = genai.Client(api_key=api_key)
              # text-embedding-004 es el modelo estándar recomendado
              response = client.models.embed_content(
                  model="text-embedding-004",
                  contents=text
              )
              if response and response.embeddings:
                  return response.embeddings[0].values
          except Exception as e:
              print(f"Error generando embedding con Gemini: {e}")
          return None

      def backfill_embeddings(self, progress_callback=None) -> int:
          """Calcula los embeddings para todos los chunks existentes que no lo tengan."""
          db = SessionLocal()
          try:
              chunks = db.query(NormativaChunk).filter(NormativaChunk.embedding_json.is_(None)).all()
              total = len(chunks)
              updated_count = 0
              
              for idx, chunk in enumerate(chunks):
                  if progress_callback:
                      progress_callback(int((idx / total) * 100), f"Procesando vector {idx+1} de {total}...")
                      
                  vector = self._get_embedding(chunk.content)
                  if vector:
                      chunk.embedding_json = json.dumps(vector)
                      updated_count += 1
                      # Guardar progresivamente por lotes pequeños de 10
                      if updated_count % 10 == 0:
                          db.commit()
              
              db.commit()
              return updated_count
          finally:
              db.close()
  ```
  
  Modificar `index_all()` en `core/normativa.py` para calcular el embedding al crear el fragmento:
  ```python
                          # Guardar si no existe
                          exists = db.query(NormativaChunk).filter_by(hash_content=h).first()
                          if not exists:
                              vector = self._get_embedding(chunk_text)
                              new_chunk = NormativaChunk(
                                  source_file=file,
                                  page=i + 1,
                                  content=chunk_text,
                                  hash_content=h,
                                  embedding_json=json.dumps(vector) if vector else None
                              )
                              db.add(new_chunk)
                              indexed_count += 1
  ```
  
  Modificar `search_in_laws()` en `core/normativa.py` para que priorice la similitud de coseno sobre la búsqueda de palabras clave `ilike`:
  ```python
      def search_in_laws(self, query, limit=5):
          """
          Busca en la BD usando embeddings vectoriales por similitud de coseno.
          Si falla o no hay datos vectoriales, usa el fallback léxico tradicional.
          """
          db = SessionLocal()
          try:
              # 1. Intentar búsqueda semántica con embeddings
              query_vector = self._get_embedding(query)
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
  ```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**
  Run: `python tests/test_rag_embeddings.py`
  Expected: PASS con los mensajes: `Prueba de similitud de coseno exitosa.` y `Prueba de fallback exitosa.`

- [ ] **Step 5: Commit**
  ```bash
  git add core/normativa.py tests/test_rag_embeddings.py
  git commit -m "feat: implement semantic search and progressive backfill of embeddings in NormativaManager"
  ```

---

### Task 3: Integrar Control de Embeddings en el Panel de Administración

**Files:**
* Modify: [app/pages/5_Panel_Control.py](file:///c:/Proyectos/CesarWorkspace/dian_sim/app/pages/5_Panel_Control.py) o el panel correspondiente de administración.

*Nota de Inspección: Debemos comprobar dónde se gestiona la normativa en la UI para agregar el botón en la página correcta (por ejemplo, en el Panel de Control, Configuración o una página de Administración de Normativa).*

- [ ] **Step 1: Inspeccionar páginas de administración**
  Revisar qué páginas manejan la indexación de normativa para colocar el botón de regeneración/backfill.

- [ ] **Step 2: Modificar la página de administración identificada**
  Añadir el botón de "Calcular Vectores Semánticos" en la UI de Streamlit:
  ```python
  st.write("### 🔍 Indexación Vectorial Semántica (RAG)")
  if st.button("🔄 Calcular Vectores de Normativa", use_container_width=True):
      manager = NormativaManager()
      with st.spinner("Generando vectores para la normativa..."):
          # Usar progress bar
          progress_bar = st.progress(0)
          status_text = st.empty()
          
          def progress_update(pct, msg):
              progress_bar.progress(pct / 100.0)
              status_text.text(msg)
              
          updated = manager.backfill_embeddings(progress_callback=progress_update)
          st.success(f"¡Sincronización completa! Se generaron vectores para {updated} fragmentos de ley.")
  ```

- [ ] **Step 3: Compilar y verificar sintaxis de la página modificada**
  Run: `python -m py_compile app/pages/5_Panel_Control.py` (o la ruta que resulte de la inspección)
  Expected: Sin errores.

- [ ] **Step 4: Commit**
  ```bash
  git add app/pages/<admin_page>.py
  git commit -m "feat: add backfill embeddings button to the admin interface"
  ```
