@echo off
cd /d "%~dp0"
echo ==========================================
echo      Configurando DIAN SIMULATOR
echo ==========================================

echo [1/3] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error instalando dependencias. Verifica que Python este instalado y en el PATH.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Inicializando base de datos...
python scripts/init_db.py
if %errorlevel% neq 0 (
    echo Error inicializando la base de datos.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Iniciando aplicacion...
echo Se abrira en tu navegador por defecto...
streamlit run app/app.py
pause
