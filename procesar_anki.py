import pandas as pd
import re
import os

# Rutas de archivos
ruta_descargas = r"C:\Users\Usuario\Downloads"
archivo_origen = os.path.join(ruta_descargas, "Anki_Dian_Fallas_20260712.csv")
archivo_destino = os.path.join(ruta_descargas, "Anki_Dian_Multiple_Corregido.csv")

print(f"Leyendo archivo desde: {archivo_origen}")

# 1. Cargar el archivo original
df = pd.read_csv(archivo_origen, sep=';', header=None, encoding='latin-1')

# 2. Lista para guardar las filas procesadas
datos_procesados = []

for index, row in df.iterrows():
    # Asegurar que no hay nulos
    col0 = str(row[0]) if pd.notna(row[0]) else ""
    col1 = str(row[1]) if pd.notna(row[1]) else ""
    
    # 3. Extracción mediante Expresiones Regulares
    tema = re.search(r'<b>Tema:</b> (.*?)(?:<br>|$)', col0)
    pregunta = re.search(r'<b>Pregunta:</b> (.*?)(?:<br><br><b>Opciones:</b>|$)', col0, re.DOTALL)
    opciones = re.findall(r'<b>([A-C]\))</b> (.*?)(?:<br>|$)', col0)
    respuesta = re.search(r'<b>Respuesta Correcta:</b> (.*?)(?:<br>|$)', col1)
    justificacion = re.search(r'<b>Justificación:</b> (.*?)(?:<br>|$)', col1)
    norma = re.search(r'<b>Norma/Referencia:</b> (.*?)(?:<br>|$)', col1)
    
    # 4. Construir la nueva fila estructurada
    nueva_fila = {
        'Tema': tema.group(1).strip() if tema else "",
        'Pregunta': pregunta.group(1).strip() if pregunta else "",
        'Opcion_A': opciones[0][1].strip() if len(opciones) > 0 else "",
        'Opcion_B': opciones[1][1].strip() if len(opciones) > 1 else "",
        'Opcion_C': opciones[2][1].strip() if len(opciones) > 2 else "",
        'Respuesta_Correcta': respuesta.group(1).strip() if respuesta else "",
        'Justificacion': justificacion.group(1).strip() if justificacion else "",
        'Norma': norma.group(1).strip() if norma else ""
    }
    datos_procesados.append(nueva_fila)

# 5. Exportar el nuevo DataFrame limpio
df_nuevo = pd.DataFrame(datos_procesados)
df_nuevo.to_csv(archivo_destino, sep=';', index=False, encoding='utf-8')
print(f"Archivo transformado y guardado en: {archivo_destino}")
print(f"Total de registros procesados: {len(df_nuevo)}")
