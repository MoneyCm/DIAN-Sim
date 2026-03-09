import streamlit as st
import os
import sqlite3
from sqlalchemy import create_engine, inspect

st.title("🔧 Diagnóstico de Base de Datos (In-App)")

# 1. Check path
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dian_sim.db"))
st.write(f"**Path calculado:** `{db_path}`")
st.write(f"**Existe archivo?**: {os.path.exists(db_path)}")

# 2. Check schema via SQLAlchemy
try:
    from db.session import engine
    st.write(f"**Engine URL:** `{engine.url}`")
    
    inspector = inspect(engine)
    cols = inspector.get_columns("user_stats")
    col_names = [c["name"] for c in cols]
    
    st.subheader("Columnas en 'user_stats' (vía SQLAlchemy + App Engine)")
    st.write(col_names)
    
    if "last_ia_date" not in col_names:
        st.error("❌ 'last_ia_date' NO encontrada.")
        if st.button("🛠️ Inyectar Columnas (SQLAlchemy App Engine)"):
             with engine.connect() as conn:
                 from sqlalchemy import text
                 try:
                     conn.execute(text("ALTER TABLE user_stats ADD COLUMN last_ia_date TIMESTAMP"))
                     st.success("last_ia_date agregada.")
                 except Exception as e:
                     st.warning(f"Error last_ia_date: {e}")
                 
                 try:
                     conn.execute(text("ALTER TABLE user_stats ADD COLUMN ia_count_today INTEGER DEFAULT 0"))
                     st.success("ia_count_today agregada.")
                 except Exception as e:
                     st.warning(f"Error ia_count_today: {e}")
                 st.rerun()
    else:
        st.success("✅ 'last_ia_date' encontrada.")

except Exception as e:
    st.error(f"Error inspeccionando SQLAlchemy: {e}")

st.divider()

# 3. Check schema via Direct SQLite
try:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_stats)")
        cols_sqlite = [r[1] for r in cursor.fetchall()]
        conn.close()
        
        st.subheader("Columnas en 'user_stats' (vía Direct SQLite Connect)")
        st.write(cols_sqlite)
    else:
        st.error("No se puede verificar SQLite directo, archivo no hallado.")

except Exception as e:
    st.error(f"Error inspeccionando SQLite directo: {e}")
st.divider()

# 4. Search for ghost content
st.subheader("👻 Búsqueda de Contenido Fantasma (Horizonte/CNSC)")
try:
    with engine.connect() as conn:
        from sqlalchemy import text
        
        st.write("### Casos sospechosos en CaseStudy")
        res_cases = conn.execute(text("""
            SELECT id, title FROM case_studies 
            WHERE title ILIKE '%Horizonte%' 
            OR text ILIKE '%Horizonte%' 
            OR text ILIKE '%CNSC%'
        """)).fetchall()
        
        if res_cases:
            st.warning(f"Se encontraron {len(res_cases)} casos!")
            for r in res_cases:
                st.write(f"- ID: `{r[0]}` | Título: `{r[1]}`")
                if st.button(f"🗑️ Eliminar Caso {r[0][:8]}", key=f"del_c_{r[0]}"):
                    conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": r[0]})
                    conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": r[0]})
                    conn.commit()
                    st.success("Eliminado. Recarga la página.")
        else:
            st.success("No se encontraron casos con términos prohibidos en la DB actual.")

        st.write("### Preguntas sospechosas sueltas")
        res_qs = conn.execute(text("""
            SELECT question_id, LEFT(stem, 50) FROM questions 
            WHERE stem ILIKE '%Horizonte%' 
            OR stem ILIKE '%CNSC%'
        """)).fetchall()
        
        if res_qs:
            st.warning(f"Se encontraron {len(res_qs)} preguntas!")
            for r in res_qs:
                st.write(f"- ID: `{r[0]}` | Stem: `{r[1]}...`")
                if st.button(f"🗑️ Eliminar Pregunta {r[0][:8]}", key=f"del_q_{r[0]}"):
                    conn.execute(text("DELETE FROM questions WHERE question_id = :id"), {"id": r[0]})
                    conn.commit()
                    st.success("Eliminada. Recarga la página.")
        else:
            st.success("No se encontraron preguntas con términos prohibidos.")

except Exception as e:
    st.error(f"Error en búsqueda fantasma: {e}")
