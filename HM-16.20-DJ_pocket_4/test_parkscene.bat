@echo off
setlocal
cd /d "%~dp0"
python run_encode.py
if errorlevel 1 exit /b 1
python verify.py
if errorlevel 1 exit /b 1
python check_border.py
exit /b %errorlevel%
