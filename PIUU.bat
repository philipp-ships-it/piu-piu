@echo off
setlocal
cd /d "%~dp0"
title PIU PIU - Terminal Arcade
if defined PIU_PYTHON goto run
where py >nul 2>nul
if not errorlevel 1 (
  py -3 piuu.py %*
  goto finished
)
where python >nul 2>nul
if not errorlevel 1 (
  set "PIU_PYTHON=python"
  goto run
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PIU_PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto run
)
echo Python wurde nicht gefunden. Ein vorhandenes, freigegebenes Python 3.10+ verwenden.
echo Bei Firmenblockade bitte die IT kontaktieren. Sicherheitssoftware nicht deaktivieren.
echo Hilfe: handbuch\FEHLERBEHEBUNG.md
pause
exit /b 3
:run
"%PIU_PYTHON%" piuu.py %*
:finished
set "PIU_EXIT=%errorlevel%"
if not "%PIU_EXIT%"=="0" pause
exit /b %PIU_EXIT%
