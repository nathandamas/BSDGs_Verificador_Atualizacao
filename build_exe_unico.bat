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

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release

pyinstaller --clean --noconfirm BSDGs_Verificador_Atualizacao.spec
if errorlevel 1 (
  echo.
  echo Falha ao gerar o executavel.
  pause
  exit /b 1
)

mkdir release
copy /Y "dist\BSDGs_Verificador_Atualizacao.exe" "release\BSDGs_Verificador_Atualizacao.exe" >nul

for %%F in ("release\BSDGs_Verificador_Atualizacao.exe") do (
  echo.
  echo Arquivo unico gerado com sucesso:
  echo %%~fF
  echo Tamanho: %%~zF bytes
)

echo.
echo Para distribuir, envie somente o arquivo da pasta release.
pause
