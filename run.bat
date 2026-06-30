@echo off
REM Start OXCAD with virtual environment
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m cadapp.main
pause
