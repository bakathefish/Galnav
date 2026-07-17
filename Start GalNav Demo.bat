@echo off
REM ==============================================================
REM  GalNav demo launcher -- double-click this file at the booth.
REM  Opens the "photo in -> position + age out" window.
REM ==============================================================
cd /d "%~dp0"
title GalNav demo (close this black window to quit the app)
echo Starting the GalNav demo window...
echo If nothing appears, make sure Python is installed and on PATH.
python -m gui.app
if errorlevel 1 (
  echo.
  echo The app exited with an error. Press any key to close.
  pause >nul
)
