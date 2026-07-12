import glob
import os

files = glob.glob('app/pages/*.py')
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    modified = False
    new_lines = []
    for line in lines:
        if 'st.set_page_config' in line and not line.strip().startswith('#'):
            new_lines.append('# ' + line)
            modified = True
            print(f"Modificado {f}")
        else:
            new_lines.append(line)
            
    if modified:
        with open(f, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)

print("Proceso finalizado.")
