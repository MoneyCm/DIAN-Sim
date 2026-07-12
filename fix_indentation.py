import os
import re

def fix_page_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex para encontrar st.set_page_config(...) incluso si es multilínea
    # Busca st.set_page_config seguido de un paréntesis abierto, y luego cualquier cosa hasta el paréntesis de cierre equilibrado
    # Esta versión es un poco más robusta para multilínea
    pattern = r'st\.set_page_config\s*\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)'
    
    # También manejar si ya está parcialmente comentado para evitar el IndentationError
    # Si la línea empieza con # pero el bloque sigue indented, lo comentamos todo o lo borramos.
    
    fixed_content = re.sub(pattern, 'pass # Removed st.set_page_config', content, flags=re.DOTALL)
    
    # Caso especial donde ya se comentó la primera línea pero quedaron las de adentro colgando
    # Buscamos líneas que parecen ser argumentos de st.set_page_config que quedaron huérfanos
    # Esto es más arriesgado, así que seremos específicos con el patrón detectado en la captura
    orphan_pattern = r'#\s*st\.set_page_config\s*\(\s*\n(?:\s+[^)]+\n)+\s*\)'
    fixed_content = re.sub(orphan_pattern, 'pass # Removed orphaned st.set_page_config block', fixed_content, flags=re.MULTILINE)

    if content != fixed_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True
    return False

pages_dir = 'app/pages'
for filename in os.listdir(pages_dir):
    if filename.endswith('.py'):
        path = os.path.join(pages_dir, filename)
        if fix_page_config(path):
            print(f"Fixed indent/config in {filename}")

print("Done.")
