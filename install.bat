@echo off
REM Install OXCAD on a new Windows computer
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo requirements.txt saknas. Skapa filen och försök igen.
    exit /b 1
)
necho Installationen är klar.
echo Kör run.bat för att starta programmet.
pause
