@echo off
setlocal
cd /d "%~dp0"

py -3.12 -m venv .venv
if errorlevel 1 py -3.11 -m venv .venv
if errorlevel 1 (
  echo Nao foi possivel criar o ambiente virtual. Instale Python 3.11 ou 3.12.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo.
echo Ambiente preparado em .venv
pause
