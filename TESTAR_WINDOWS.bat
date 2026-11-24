@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Execute CONFIGURAR_WINDOWS.bat primeiro.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 (
    echo [ERRO] Um ou mais testes falharam. Confira o resultado acima.
) else (
    echo [OK] Testes concluidos.
)
pause
