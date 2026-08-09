@echo off
cd /d "%~dp0"
echo ==========================================
echo  DianSim - Gestor III OPEC 236769
echo ==========================================

set "LOCAL_PYTHON=%~dp0.venv\Scripts\python.exe"
set "DATABASE_URL=sqlite:///%~dp0dian_sim_opec236769.db"
set "DIAN_SIM_ENV=development"
set "REQUIRE_DATABASE_URL=false"

if not exist "%LOCAL_PYTHON%" (
    echo No se encontro el entorno virtual en .venv.
    pause
    exit /b 1
)

if not exist "%~dp0dian_sim_opec236769.db" (
    echo No se encontro la base OPEC 236769. Ejecuta la migracion de datos primero.
    pause
    exit /b 1
)

echo Base de datos: dian_sim_opec236769.db
echo URL: http://localhost:8501
"%LOCAL_PYTHON%" -m streamlit run app/app.py
pause
