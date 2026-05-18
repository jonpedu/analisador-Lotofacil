@echo off
echo ===================================================
echo       Iniciando o Lotofacil Analyzer Pro...
echo ===================================================

cd /d "%~dp0"

:: Tenta ativar o ambiente virtual (venv ou .venv)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [i] Ambiente virtual 'venv' ativado.
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [i] Ambiente virtual '.venv' ativado.
) else (
    echo [!] Nenhum ambiente virtual encontrado. O script tentara executar globalmente.
)

:: Verifica se o streamlit está instalado verificando com python -m streamlit
python -c "import streamlit" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ===================================================
    echo  AVISO: Streamlit nao parece estar instalado.
    echo  Tentando instalar as dependencias...
    echo ===================================================
    py -m pip install -r requirements.txt
)

echo.
echo Iniciando o servidor do Streamlit...
py -m streamlit run streamlit_app.py

pause
