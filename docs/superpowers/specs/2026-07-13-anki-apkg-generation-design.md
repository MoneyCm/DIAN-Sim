# Diseño Técnico: Generación Directa de Mazos Anki (.apkg)

Este documento especifica el diseño para implementar la generación directa de archivos `.apkg` de Anki en el simulador `dian_sim`. El objetivo es simplificar la experiencia de usuario (UX), permitiendo instalar barajas interactivas completas con un solo doble clic, eliminando el mapeo manual de archivos CSV y código HTML/CSS.

## 1. Cambios en las Dependencias
Se añadirá la librería `genanki` al archivo `requirements.txt`:
* **Librería:** `genanki` (última versión compatible con Python 3.13).
* **Propósito:** Generar bases de datos de Anki empaquetadas en un único archivo binario `.apkg`.

---

## 2. Nuevo Módulo de Generación: `core/anki.py`
Crearemos un módulo centralizado para encapsular toda la lógica de Anki:

### 2.1 Identificadores Únicos Estables (IDs)
Anki requiere números enteros de 32/64 bits únicos para identificar modelos y barajas. Para evitar duplicados en la base de datos de Anki de los usuarios, definiremos IDs fijos:
* **Model ID:** `1583094821` (ID fijo para el tipo de nota "DIAN - Interactivo 10 Columnas").
* **Base Deck ID:** `2026071301` (ID base para las barajas de la DIAN).

### 2.2 Definición del Tipo de Nota (Modelo de 10 campos)
El modelo `genanki.Model` contendrá los siguientes elementos:
* **Campos:** 
  1. `Caso_Estudio`
  2. `Tema`
  3. `Pregunta`
  4. `Opcion_A`
  5. `Opcion_B`
  6. `Opcion_C`
  7. `Opcion_D`
  8. `Respuesta_Correcta`
  9. `Justificacion`
  10. `Norma`
* **Plantilla Anverso (Front Template):** El código HTML interactivo optimizado para soportar casos de estudio y descartes de la opción D.
* **Estilo CSS (Styling):** Los estilos visuales oscuros, bordes redondeados y micro-animaciones en los botones.
* **Plantilla Reverso (Back Template):** El código HTML del reverso con la justificación y referencias normativas visibles.

### 2.3 Función de Conversión
La función `generate_anki_deck(questions: List[Question], deck_name: str) -> bytes` se encargará de:
1. Crear una baraja con el nombre proporcionado (ej. "DIAN - Preguntas Falladas" o "DIAN - Favoritas").
2. Iterar sobre las preguntas convirtiendo cada registro en una nota (`genanki.Note`) asociada al modelo interactivo.
3. Escribir el paquete `.apkg` a un archivo temporal usando `tempfile.NamedTemporaryFile`.
4. Leer los bytes del archivo temporal, eliminar el archivo físico del disco y retornar los bytes listos para la descarga.

---

## 3. Interfaz de Usuario en `app/pages/6_Dashboard.py`
Modificaremos la pestaña interactiva del Dashboard para incorporar los nuevos botones de descarga APKG:

### 3.1 Nuevos Botones en Streamlit
Al lado de los botones de descarga de CSV existentes, agregaremos botones para descargar el mazo directo de Anki:
* **Fallas:** `"📥 Descargar Mazo APKG (Fallas)"`
* **Favoritas:** `"📥 Descargar Mazo APKG (Favoritas)"`

### 3.2 Lógica de Descarga en Streamlit
El flujo de Streamlit para el botón APKG será:
```python
anki_bytes = generate_anki_deck(failed_qs, "DIAN - Preguntas Falladas")
st.download_button(
    label="📥 Descargar Mazo APKG (Fallas)",
    data=anki_bytes,
    file_name=f"DIAN_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
    mime="application/apkg",
    key="btn_export_anki_fallas_apkg"
)
```

### 3.3 Instrucciones Simplificadas
Actualizaremos las instrucciones de la pestaña para indicar al usuario:
1. Descargar el archivo `.apkg`.
2. Hacer doble clic sobre él en su computadora para instalar todo de golpe.
3. Sincronizar en el móvil y comenzar a estudiar.

---

## 4. Plan de Verificación

### 4.1 Pruebas Unitarias / Funcionales
Crearemos un script de prueba en `scratch/test_genanki.py` para:
* Generar un mazo de Anki con 2 preguntas ficticias de prueba.
* Validar que el archivo `.apkg` se escriba de manera correcta sin excepciones.

### 4.2 Verificación Manual
* Ejecutaremos el simulador localmente.
* Descargaremos el archivo `.apkg` de prueba desde la interfaz.
* Abriremos el archivo `.apkg` haciendo doble clic en Anki de escritorio y confirmaremos que:
  * El tipo de nota `DIAN - Interactivo 10 Columnas` se cargue con sus 10 campos.
  * La baraja se cree con las tarjetas bien alineadas.
  * Al previsualizar la tarjeta en Anki, responda de forma interactiva y muestre los colores correspondientes.
