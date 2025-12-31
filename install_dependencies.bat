@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PYTHON_EXE=python

if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
  set PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe
)

"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"

echo.
echo Dependencies installed.
pause
endlocal
