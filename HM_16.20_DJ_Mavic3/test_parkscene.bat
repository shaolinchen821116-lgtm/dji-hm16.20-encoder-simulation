@echo off
cd /d "%~dp0"
python run_test.py
exit /b %errorlevel%
