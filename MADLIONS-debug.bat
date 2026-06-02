@echo off
rem Same as MADLIONS.bat but keeps a console open so you can see errors.
rem Use this one if the app fails to start and you want to know why.
title MADLIONS 60 Configurator (debug)
cd /d "%~dp0"
python "%~dp0main.py"
echo.
echo --- app closed (or failed to start). Any errors are shown above. ---
pause
