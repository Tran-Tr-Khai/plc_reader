
@echo off
setlocal

rem Resolve application paths.
set "APP_DIR=%~dp0"
set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"
set "LOG_DIR=%APP_DIR%logs"
set "LOG_FILE=%LOG_DIR%\plc_reader.log"

rem Validate Python environment.
if not exist "%PYTHON%" (
    echo ERROR: Python not found: "%PYTHON%"
    exit /b 1
)

rem Prepare log directory.
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem Set working directory to application directory.
cd /d "%APP_DIR%" || exit /b 1

rem Start PLC Reader.
echo [%date% %time%] Starting PLC Reader...>> "%LOG_FILE%"

"%PYTHON%" -u -m plc_reader >> "%LOG_FILE%" 2>&1

rem Capture exit code.
set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] PLC Reader exited with code %EXIT_CODE%.>> "%LOG_FILE%"

exit /b %EXIT_CODE%
