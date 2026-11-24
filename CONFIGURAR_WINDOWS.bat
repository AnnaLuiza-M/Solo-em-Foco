@echo off
setlocal
cd /d "%~dp0"
echo [Solo em Foco] Configurando o ambiente Python...
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -m venv .venv
        goto install
    )
    py -3.11 --version >nul 2>nul
    if not errorlevel 1 (
        py -3.11 -m venv .venv
        goto install
    )
)
where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Instale o Python 3.12 64 bits antes de continuar.
    pause
    exit /b 1
)
python -m venv .venv
:install
if errorlevel 1 (
    echo [ERRO] Falha ao criar .venv. Verifique a instalacao do Python.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo [OK] Dependencias instaladas. Execute TESTAR_WINDOWS.bat, depois INICIAR_WINDOWS.bat.
pause
exit /b 0
:error
echo.
echo [ERRO] Instalacao incompleta. Confira a mensagem acima.
pause
exit /b 1
