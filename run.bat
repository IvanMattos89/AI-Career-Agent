@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)

if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar o AI Career Agent.
    echo Confira se o Python e as dependencias estao instalados.
    pause
)
