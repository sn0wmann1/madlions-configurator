@echo off
rem ── MADLIONS 60 Configurator launcher ───────────────────────────────
rem Double-click this to open the app (no terminal needed).
rem Runs from this file's own folder, so you can move the project anywhere.
title MADLIONS 60 Configurator
cd /d "%~dp0"

rem Prefer pythonw (no console window). Fall back to python if not found.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0main.py"
) else (
    start "" python "%~dp0main.py"
)
