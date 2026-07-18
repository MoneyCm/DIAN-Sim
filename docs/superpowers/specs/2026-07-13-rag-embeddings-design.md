# Diseño Técnico: Búsqueda Semántica RAG con Embeddings de Gemini

Este documento especifica el diseño para implementar la búsqueda semántica basada en vectores de embeddings de Google Gemini en el sistema RAG de normativa del simulador `dian_sim`. El objetivo es mejorar significativamente la precisión en la búsqueda y entrega de referencias normativas y de estatuto tributario a las preguntas y justificaciones del simulador.

## 1. Cambios en la Base de Datos

### 1.1 Modelo `NormativaChunk`
Modificaremos la clase `NormativaChunk` en `db/models.py` para añadir la columna `embedding_json`:
```python
class NormativaChunk(Base):
    __tablename__ = "normativa_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_file: Mapped[str] = mapped_column(String)
    page: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    hash_content: Mapped[str] = mapped_column(String, unique=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # NUEVA COLUMNA
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
```

### 1.2 Migración Dinámica en `db/session.py`
Actualizaremos el mapeo `new_cols_map` en `db/session.py` para asegurar la creación automática de la columna tanto en entornos SQLite locales como en PostgreSQL en Streamlit Cloud:
```python
new_cols_map = {
    # ...
    "normativa_chunks": [("embedding_json", "TEXT")],
    # ...
}
```

---

## 2. Lógica de RAG en `core/normativa.py`
Actualizaremos el módulo `core/normativa.py` para implementar los siguientes comportamientos:

### 2.1 Generación de Embeddings
Implementar un método privado para conectarse a Gemini y obtener el embedding usando la API Key configurada en el sistema:
```python
def _get_embedding(self, text: str) -> Optional[list]:
    from core.config import get_api_key
    from google import genai
    
    api_key = get_api_key("gemini")
    if not api_key:
        return None
        
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        if response and response.embeddings:
            return response.embeddings[0].values
    except Exception as e:
        print(f"Error generando embedding: {e}")
    return None
```

### 2.2 Indexación con Vectores
Modificar `index_all()` para que durante la extracción e inserción de nuevos fragmentos de PDFs, se calcule y almacene el vector en `embedding_json` (serializado como JSON string).

### 2.3 Procesamiento Retroactivo (Backfill)
Añadir una función `backfill_embeddings(self, progress_callback=None) -> int` para rellenar los embeddings de aquellos registros de normativa preexistentes en la base de datos que se indexaron anteriormente y poseen `embedding_json` nulo.

### 2.4 Búsqueda Vectorial Híbrida
Actualizar `search_in_laws(self, query, limit=5)`:
1. Generar el vector de la consulta (`query`) usando `_get_embedding()`.
2. Si se genera con éxito:
   * Consultar todos los chunks de la base de datos que tengan `embedding_json` no nulo.
   * Si existen registros con vector, deserializar cada vector y calcular la similitud de coseno en memoria.
   * Ordenar los resultados y tomar los `limit` mejores.
3. Si falla la generación del vector de consulta o no hay vectores en la BD, la función cae automáticamente al algoritmo léxico clásico (`ilike` + `rapidfuzz`) asegurando resiliencia total.

Fórmula de similitud de coseno en Python puro (para mantener la portabilidad):
```python
def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(a * a for a in v2) ** 0.5
    if not norm_v1 or not norm_v2:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)
```

---

## 3. Plan de Verificación

### 3.1 Pruebas Unitarias
Crearemos un archivo `tests/test_rag_embeddings.py` para:
* Validar la generación de embeddings mediante `_get_embedding` con una frase de prueba.
* Verificar que la función de similitud de coseno calcula valores válidos.
* Comprobar que la búsqueda vectorial devuelve resultados ordenados por relevancia semántica.

### 3.2 Verificación Manual
* Ejecutaremos el script de backfill localmente para comprobar que los chunks existentes se actualicen.
* Realizaremos búsquedas de prueba y contrastaremos la precisión de los fragmentos recuperados.
