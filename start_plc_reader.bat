@echo off
setlocal

rem Start LS PLC Reader from its package parent directory.
rem This file is intended to be used by Windows Task Scheduler at startup.

set "APP_DIR=%~dp0"
set "PROJECT_PARENT=%APP_DIR%.."
set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"
set "LOG_DIR=%APP_DIR%logs"

if not exist "%PYTHON%" (
    echo ERROR: Python virtual environment not found: "%PYTHON%"
    exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d "%PROJECT_PARENT%"
echo [%date% %time%] Starting PLC reader...>> "%LOG_DIR%\plc_reader.log"
"%PYTHON%" -u -m plc_reader >> "%LOG_DIR%\plc_reader.log" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] PLC reader stopped with exit code %EXIT_CODE%.>> "%LOG_DIR%\plc_reader.log"

exit /b %EXIT_CODE%
