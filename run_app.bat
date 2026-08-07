@echo off
cd /d "%~dp0"
echo ==========================================
echo      Iniciando simulador local
echo ==========================================

set "LOCAL_PYTHON=%~dp0.venv\Scripts\python.exe"
set "DATABASE_URL=sqlite:///dian_sim.db"
set "DIAN_SIM_ENV=development"
set "REQUIRE_DATABASE_URL=false"

if not exist "%LOCAL_PYTHON%" (
    echo No se encontro el entorno virtual en .venv.
    echo Ejecuta primero: python -m venv .venv
    pause
    exit /b 1
)

echo Base de datos: dian_sim.db ^(SQLite local^)
echo URL: http://localhost:8501
"%LOCAL_PYTHON%" -m streamlit run app/app.py
pause
