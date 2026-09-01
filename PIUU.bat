@echo off
title PIUU PIUU 3000
where python >nul 2>nul
if errorlevel 1 (
  echo Python nicht gefunden. Bitte von https://python.org installieren.
  pause
  exit /b 1
)
python "%~dp0piuu.py" %*
pause
