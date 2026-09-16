@echo off
python "%~dp0skiff.py" %*
if errorlevel 9009 (
  echo Python not found. Install Python 2.7+ and ensure it is on PATH.
)
