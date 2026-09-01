@echo off
REM ==== PIUU PIUU 3000 -> PIUU.exe bauen ====
title PIUU Build
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [!] Python nicht gefunden. Bitte von https://python.org installieren
  echo     (beim Setup "Add Python to PATH" anhaken).
  pause & exit /b 1
)

echo [1/3] PyInstaller installieren/aktualisieren...
python -m pip install --upgrade pip pyinstaller || (echo [!] pip fehlgeschlagen & pause & exit /b 1)

echo [2/3] Exe bauen...
python -m PyInstaller --onefile --console --name PIUU piuu.py || (echo [!] Build fehlgeschlagen & pause & exit /b 1)

echo [3/3] Fertig!
copy /y "dist\PIUU.exe" "PIUU.exe" >nul
echo.
echo   ==^> PIUU.exe liegt jetzt hier: %cd%\PIUU.exe
echo   Einfach doppelklicken. Kein Python noetig auf anderen PCs.
echo.
pause
