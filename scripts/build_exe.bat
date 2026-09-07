@echo off
setlocal
cd /d "%~dp0.."
if not defined PIU_PYTHON set "PIU_PYTHON=python"
"%PIU_PYTHON%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo Python oder PyInstaller fehlt. Siehe handbuch\ENTWICKLUNG.md.
  echo Es werden keine Pakete automatisch installiert.
  exit /b 1
)
"%PIU_PYTHON%" -m PyInstaller --clean --onefile --console --name PIUU piuu.py
if errorlevel 1 exit /b 1
echo Fertig: dist\PIUU.exe. Profildaten bleiben im Benutzerdatenordner.
