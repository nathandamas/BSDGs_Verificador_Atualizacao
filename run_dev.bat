@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Execute install_dev.bat primeiro.
  pause
  exit /b 1
)
.venv\Scripts\python.exe main.py
