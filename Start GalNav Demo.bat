@echo off
REM ==============================================================
REM  GalNav demo launcher -- double-click this file at the booth.
REM  Starts the web demo and opens it in your browser
REM  (photo in -> position + catalog age + 3-D map out).
REM  The older desktop window remains available via: python -m gui.app
REM ==============================================================
cd /d "%~dp0"
title GalNav demo server (close this black window to quit the app)
echo Starting the GalNav web demo (your browser will open)...
echo If nothing appears, make sure Python is installed and on PATH,
echo then open http://127.0.0.1:8000 yourself.
python -m gui.webapp
if errorlevel 1 (
  echo.
  echo The app exited with an error. Press any key to close.
  pause >nul
)
