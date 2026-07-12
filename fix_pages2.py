import glob
import re
import os

files = glob.glob('app/pages/*.py')
# Regex para encontrar st.set_page_config( ... ) incluyendo todo su interior multilinea
pattern = re.compile(r'^[ \t]*#?[ \t]*st\.set_page_config\s*\([^)]+\)', re.MULTILINE)

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    modified_content, subs = pattern.subn('pass # Removed st.set_page_config for st.navigation', content)
    
    # Algunas paginas pueden tener parentesis cerrando en la siguiente linea
    pattern_hanging = re.compile(r'^[ \t]*#?[ \t]*st\.set_page_config\s*\(.*?\n([ \t]*[a-zA-Z_]+[ \t]*=.*?\n)*[ \t]*\)', re.MULTILINE | re.DOTALL)
    modified_content, subs2 = pattern_hanging.subn('pass # Removed multiline st.set_page_config', modified_content)

    if subs > 0 or subs2 > 0:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        print(f"Sanitized: {f}")

print("Clean process finished.")
