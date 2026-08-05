@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BSDGs - Build Windows x64

echo ============================================================
echo BSDGs - Verificador de Atualizacao v1.3.0
echo Compilacao Windows x64 / AMD64
echo ============================================================
echo.

python -c "import platform,struct,sys; a=platform.machine().upper(); b=struct.calcsize('P')*8; print('Python:',sys.version.split()[0],'| Arquitetura:',a,'| Bits:',b); sys.exit(0 if a in ('AMD64','X86_64') and b==64 else 2)"
if errorlevel 1 (
  echo.
  echo ERRO: este build exige Python Windows x64 / AMD64 de 64 bits.
  echo Instale o Python x64 e recrie o ambiente antes de continuar.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 goto :erro
python -m pip install -r requirements-dev.txt pytest
if errorlevel 1 goto :erro
python -m pytest -q
if errorlevel 1 goto :erro

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --clean --noconfirm BSDGs_Verificador_Atualizacao.spec
if errorlevel 1 goto :erro

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$src='dist\BSDGs_Verificador_Atualizacao.exe'; $dst='dist\BSDGs_Verificador_Atualizacao_v1.3.0_windows_x64.exe'; Move-Item $src $dst -Force; $s=[IO.File]::OpenRead($dst); $r=[IO.BinaryReader]::new($s); try {$s.Position=0x3C; $o=$r.ReadInt32(); $s.Position=$o+4; $m=$r.ReadUInt16()} finally {$r.Dispose();$s.Dispose()}; if($m-ne 0x8664){throw ('PE incorreto: 0x{0:X4}' -f $m)}; $h=Get-FileHash $dst -Algorithm SHA256; ($h.Hash+'  '+[IO.Path]::GetFileName($dst)) | Set-Content ($dst+'.sha256') -Encoding ascii; Write-Host 'PE confirmado: Windows x64 / AMD64'; Get-Item $dst | Format-List Name,Length"
if errorlevel 1 goto :erro

echo.
echo Build concluido:
echo %CD%\dist\BSDGs_Verificador_Atualizacao_v1.3.0_windows_x64.exe
pause
exit /b 0

:erro
echo.
echo ERRO: a compilacao nao foi concluida.
pause
exit /b 1
