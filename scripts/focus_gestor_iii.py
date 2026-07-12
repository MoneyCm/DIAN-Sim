import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Rutas del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sqlite_db_path = os.path.join(PROJECT_ROOT, "dian_sim.db")

# Datos oficiales del cargo Gestor III (OPEC 236769)
OPEC_NUMBER = "236769"
JOB_TITLE = "Gestor III (OPEC 236769)"
LEVEL = "Profesional"
PURPOSE = ("AT-FL-3006. DESARROLLAR, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, "
           "INVESTIGACIONES PARA LA VERIFICACION DEL CUMPLIMIENTO DE OBLIGACIONES EN MATERIA "
           "TRIBUTARIA, ADUANERA O CAMBIARIA, ASI COMO LA DETECCION DE PRACTICAS TENDIENTES A "
           "LA ELUSION, EVASION, ABUSO, CONTRABANDO Y LAVADO DE ACTIVOS, DE ACUERDO CON LA "
           "NORMATIVA VIGENTE, LOS PROCEDIMIENTOS ESTABLECIDOS Y LAS DIRECTRICES INSTITUCIONALES.")

FUNCTIONS = [
    "HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION RECIBIDAS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA ACCION DE FISCALIZACION, DE ACUERDO CON LA NORMATIVA VIGENTE, PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.",
    "HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS RECIBIDOS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA INVESTIGACION, DE ACUERDO CON LOS PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.",
    "LAS SEÑALADAS COMO COMUNES A TODOS LOS EMPLEOS DE LA PLANTA DE PERSONAL DE LA ENTIDAD, INCLUIDAS EN LA RESOLUCION QUE ADOPTA O MODIFICA EL MANUAL Y LAS DEMAS ASIGNADAS POR AUTORIDAD COMPETENTE, DE ACUERDO CON EL NIVEL, GRADO DE RESPONSABILIDAD Y EL AREA DE DESEMPEÑO DEL EMPLEO.",
    "ORGANIZAR LA INFORMACION Y PROPUESTAS DE ASUNTOS DE FISCALIZACION PARA PRESENTARLOS A CONSIDERACION DE LA REUNION DEL NIVEL DIRECTIVO DEL PROCESO DE FISCALIZACION Y LIQUIDACION PARA LA DECISION PERTINENTE.",
    "PARTICIPAR EN LA EJECUCION DE ACCIONES DE FISCALIZACION, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, TENDIENTES A LA VERIFICACION DEL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS, DE ACUERDO CON LA NORMATIVA VIGENTE, LINEAMIENTOS INSTITUCIONALES Y PROCEDIMIENTOS ESTABLECIDOS.",
    "PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE, PREPARATORIOS Y DE FONDO REQUERIDOS DENTRO DEL PROCESO, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.",
    "REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS Y, EL REPORTE DE LAS OPERACIONES SOSPECHOSAS DE LAVADO DE ACTIVOS Y FINANCIACION DEL TERRORISMO, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, DE ACUERDO CON LA NORMATIVA VIGENTE, LAS DIRECTRICES INSTITUCIONALES Y LOS PROCEDIMIENTOS ESTABLECIDOS.",
    "REALIZAR LA PRACTICA DE PRUEBAS SOLICITADAS POR UNA DEPENDENCIA DEL NIVEL CENTRAL O SECCIONAL, PARA QUE OBRE DENTRO DE UNA INVESTIGACION, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.",
    "REVISAR TECNICA Y O JURIDICAMENTE, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, LOS EXPEDIENTES Y ASUNTOS ASIGNADOS PROPIOS DEL PROCESO, DE ACUERDO CON LA NORMATIVA VIGENTE Y LAS DIRECTRICES INSTITUCIONALES."
]

REQUIREMENTS = (
    "Estudio: Título de PROFESIONAL en NBC: ADMINISTRACION ,O, NBC: CIENCIA POLITICA, "
    "RELACIONES INTERNACIONALES ,O, NBC: CONTADURIA PUBLICA ,O, NBC: DERECHO Y AFINES ,O, "
    "NBC: ECONOMIA ,O, NBC: INGENIERIA ADMINISTRATIVA Y AFINES ,O, NBC: INGENIERIA DE "
    "SISTEMAS, TELEMATICA Y AFINES ,O, NBC: INGENIERIA INDUSTRIAL Y AFINES ,O, NBC: "
    "INGENIERIA QUIMICA Y AFINES ,O, NBC: MATEMATICAS, ESTADISTICA Y AFINES.\n"
    "Experiencia: Doce (12) meses de EXPERIENCIA PROFESIONAL RELACIONADA, Y, Doce (12) meses de EXPERIENCIA PROFESIONAL.\n"
    "Otros: Tarjeta Profesional en los casos señalados por la Ley."
)

def update_database(db_url, db_name):
    print(f"\n🌐 Sincronizando Base de Datos: {db_name}...")
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            # 1. Obtener la lista de usuarios
            res_users = conn.execute(text("SELECT id, username FROM users")).fetchall()
            if not res_users:
                print(f"⚠️ No se encontraron usuarios en {db_name}.")
                return

            print(f"👥 Usuarios detectados: {[u.username for u in res_users]}")

            for user in res_users:
                user_id = user.id
                username = user.username

                # Desactivar cualquier otra OPEC que tenga el usuario
                conn.execute(text("UPDATE user_opec SET is_active = False WHERE user_id = :u_id"), {"u_id": user_id})

                # Verificar si ya existe la OPEC 236769 para este usuario
                existing = conn.execute(
                    text("SELECT id FROM user_opec WHERE user_id = :u_id AND opec_number = :opec"),
                    {"u_id": user_id, "opec": OPEC_NUMBER}
                ).first()

                functions_json = json.dumps(FUNCTIONS)

                if existing:
                    # Actualizar
                    print(f"🔄 Actualizando meta activa OPEC {OPEC_NUMBER} para {username} (ID {user_id})...")
                    conn.execute(text("""
                        UPDATE user_opec 
                        SET job_title = :title,
                            level = :level,
                            purpose = :purpose,
                            functions = :funcs,
                            requirements = :reqs,
                            is_active = True
                        WHERE user_id = :u_id AND opec_number = :opec
                    """), {
                        "title": JOB_TITLE,
                        "level": LEVEL,
                        "purpose": PURPOSE,
                        "funcs": functions_json,
                        "reqs": REQUIREMENTS,
                        "u_id": user_id,
                        "opec": OPEC_NUMBER
                    })
                else:
                    # Insertar
                    print(f"✨ Creando nueva meta activa OPEC {OPEC_NUMBER} para {username} (ID {user_id})...")
                    conn.execute(text("""
                        INSERT INTO user_opec (user_id, opec_number, job_title, level, purpose, functions, requirements, is_active)
                        VALUES (:u_id, :opec, :title, :level, :purpose, :funcs, :reqs, True)
                    """), {
                        "u_id": user_id,
                        "opec": OPEC_NUMBER,
                        "title": JOB_TITLE,
                        "level": LEVEL,
                        "purpose": PURPOSE,
                        "funcs": functions_json,
                        "reqs": REQUIREMENTS
                    })
        
        print(f"✅ Sincronización exitosa en {db_name}.")
    except Exception as e:
        print(f"❌ Error al sincronizar {db_name}: {e}")

def main():
    print("🚀 INICIANDO ENFOQUE GESTOR III (OPEC 236769) EN BASE DE DATOS...")

    # 1. Base de datos SQLite Local
    sqlite_url = f"sqlite:///{sqlite_db_path}"
    update_database(sqlite_url, "SQLite Local (dian_sim.db)")

    # 2. Base de datos Neon PostgreSQL (Nube)
    neon_url = os.getenv("DATABASE_URL")
    if neon_url:
        # Asegurar dialecto psycopg2 en SQLAlchemy
        if neon_url.startswith("postgres://") or neon_url.startswith("postgresql://"):
            neon_url = neon_url.replace("postgres://", "postgresql+psycopg2://", 1)
            neon_url = neon_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
            # Limpiar parámetros conflictivos de Neon
            if "channel_binding=" in neon_url:
                import re
                neon_url = re.sub(r'[&?]channel_binding=[^&]*', '', neon_url)
                
        update_database(neon_url, "PostgreSQL Cloud (Neon)")
    else:
        print("\n⚠️ No se detectó DATABASE_URL en el entorno. Se omitió la actualización de la nube.")

    print("\n🏁 ¡PROCESO DE ENFOQUE FINALIZADO CON ÉXITO!")

if __name__ == "__main__":
    main()
