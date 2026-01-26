import pandas as pd

REQUIRED_COLUMNS = [
    'track', 
    'competency', 
    'topic', 
    'stem', 
    'options_A', 
    'options_B', 
    'options_C', 
    'correct_key'
]

def validate_import_df(df: pd.DataFrame):
    """
    Valida que el DataFrame tenga las columnas requeridas y no tenga celdas críticas vacías.
    Retorna (es_valido, lista_errores)
    """
    errors = []
    
    # 1. Verificar columnas
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Faltan las columnas: {', '.join(missing_cols)}")
        return False, errors

    # 2. Verificar filas
    for index, row in df.iterrows():
        row_num = index + 2 # Excel starts at 1, +1 for header
        
        # Campos que no pueden ser nulos
        critical_fields = ['track', 'stem', 'correct_key', 'options_A', 'options_B', 'options_C']
        for field in critical_fields:
            if pd.isna(row[field]) or str(row[field]).strip() == "":
                errors.append(f"Fila {row_num}: El campo '{field}' está vacío.")
        
        # Opciones D es opcional (algunas IAs generan 3 opciones)
        if 'options_D' in row and not pd.isna(row['options_D']) and str(row['options_D']).strip() != "":
            pass # Válido
        
        # Validar llave de respuesta
        if not pd.isna(row['correct_key']):
            if str(row['correct_key']).strip().upper() not in ['A', 'B', 'C', 'D']:
                errors.append(f"Fila {row_num}: La respuesta correcta debe ser A, B, C o D.")

        # Validar dificultad (opcional pero debe ser entero si existe)
        if 'difficulty' in row and not pd.isna(row['difficulty']):
            try:
                d = int(float(row['difficulty']))
                if d < 1 or d > 5:
                    errors.append(f"Fila {row_num}: La dificultad debe estar entre 1 y 5.")
            except (ValueError, TypeError):
                errors.append(f"Fila {row_num}: La dificultad debe ser un número entero.")

    is_valid = len(errors) == 0
    return is_valid, errors
