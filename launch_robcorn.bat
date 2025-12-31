@echo off
setlocal

rem Launch RobCron from source.
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=python
set PYTHONPATH=%SCRIPT_DIR%src

if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
  set PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe
)

start "" /b "%PYTHON_EXE%" "%SCRIPT_DIR%api\server.py"
"%PYTHON_EXE%" -m robcorn.main
endlocal
