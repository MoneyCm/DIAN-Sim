import os
import pypdf
import re

class NormativaManager:
    def __init__(self, folder_path="data/normativa"):
        self.folder_path = folder_path

    def search_in_laws(self, query):
        """
        Busca fragmentos relevantes en los PDFs de la carpeta normativa.
        Retorna los textos que coincidan con la búsqueda. Mikey
        """
        results = []
        if not os.path.exists(self.folder_path):
            return results

        # Simple keyword search for MVP (Phase 4 Start)
        keywords = re.findall(r'\b\w+\b', query.lower())
        
        for file in os.listdir(self.folder_path):
            if file.endswith(".pdf"):
                full_path = os.path.join(self.folder_path, file)
                try:
                    with open(full_path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for i, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if any(k in text.lower() for k in keywords if len(k) > 3):
                                # Extract snippet
                                results.append({
                                    "source": file,
                                    "page": i + 1,
                                    "snippet": text[:500] + "..." # Limit snippet size
                                })
                                if len(results) > 3: break # Limit results
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        
        return results

    def get_law_context(self, topic):
        """
        Obtiene contexto legal específico para inyectar en el generador. Mikey
        """
        snippets = self.search_in_laws(topic)
        if not snippets:
            return ""
        
        context = "\n\n--- REFERENCIAS LEGALES REALES ---\n"
        for s in snippets:
            context += f"Fuente: {s['source']} (Pág. {s['page']}):\n{s['snippet']}\n"
        return context
