@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente .venv nao encontrado. Execute CONFIGURAR_WINDOWS.bat primeiro.
    pause
    exit /b 1
)
echo [Solo em Foco] Servidor: http://127.0.0.1:8000
echo [Solo em Foco] Para parar: pressione Ctrl+C.
.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
if errorlevel 1 (
    echo [ERRO] O servidor foi encerrado com erro.
    pause
    exit /b 1
)
