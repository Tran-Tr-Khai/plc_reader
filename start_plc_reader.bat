@echo off
setlocal

rem ============================================================
rem PLC Reader startup script
rem ============================================================

rem Resolve application paths.
set "APP_DIR=%~dp0"
for %%I in ("%APP_DIR%..") do set "PROJECT_PARENT=%%~fI"

set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"
set "PYTHONPATH=%PROJECT_PARENT%"
set "LOG_DIR=%APP_DIR%logs"

rem Enable UTF-8.
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

rem Validate Python.
if not exist "%PYTHON%" (
    echo ERROR: Python not found:
    echo "%PYTHON%"
    exit /b 1
)

rem Validate PLC Reader package.
if not exist "%APP_DIR%__init__.py" (
    echo ERROR: Missing "%APP_DIR%__init__.py"
    exit /b 1
)

if not exist "%APP_DIR%__main__.py" (
    echo ERROR: Missing "%APP_DIR%__main__.py"
    exit /b 1
)

rem Create log directory.
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

rem Python must run from the package parent directory.
cd /d "%PROJECT_PARENT%" || (
    echo ERROR: Cannot open directory "%PROJECT_PARENT%"
    exit /b 1
)

rem Application logging is handled by Python's rotating file handler.
rem launcher.log only receives startup failures before logging is configured.
"%PYTHON%" -X utf8 -u -m plc_reader 1>NUL 2>> "%LOG_DIR%\launcher.log"

rem Capture exit code.
exit /b %ERRORLEVEL%
