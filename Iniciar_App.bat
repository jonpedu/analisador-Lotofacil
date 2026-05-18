@echo off
echo ===================================================
echo       Iniciando o Lotofacil Analyzer Pro...
echo ===================================================

cd /d "%~dp0"

:: Verifica se o ambiente virtual existe, se não, apenas roda o streamlit global ou tenta ativar
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Iniciando o servidor do Streamlit...
streamlit run streamlit_app.py

pause
