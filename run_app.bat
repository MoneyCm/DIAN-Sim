@echo off
cd /d "%~dp0"
echo ==========================================
echo      Configurando DIAN SIMULATOR
echo ==========================================

echo [1/2] Instalando dependencias...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error instalando dependencias. Verifica que Python este instalado y en el PATH.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/2] Iniciando aplicacion...
echo Se abrira en tu navegador por defecto...
python -m streamlit run app/app.py
pause
