@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Execute install_dev.bat primeiro.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python -c "import platform; print('Python:', platform.python_version(), '| Arquitetura:', platform.machine())"
pyinstaller --clean --noconfirm BSDGs_Verificador_Atualizacao.spec
if errorlevel 1 (
  echo.
  echo Falha ao gerar o executavel. Consulte README.md, secao Windows ARM64.
  pause
  exit /b 1
)

echo.
echo Executavel criado em:
echo %CD%\dist\BSDGs_Verificador_Atualizacao.exe
pause
