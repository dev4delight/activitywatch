@echo off
title ActivityWatch Configuration
color 0B

echo ============================================================
echo   ActivityWatch Employee Configuration
echo ============================================================
echo.

set INSTALL_DIR=%LOCALAPPDATA%\ActivityWatch-Employee
set CONFIG_FILE=%INSTALL_DIR%\aw_employee_watcher.py

if not exist "%CONFIG_FILE%" (
    set CONFIG_FILE=aw_employee_watcher.py
)

if not exist "%CONFIG_FILE%" (
    echo [ERROR] Cannot find aw_employee_watcher.py
    echo Please run install.bat first
    pause
    exit /b 1
)

echo Current configuration will be updated in:
echo   %CONFIG_FILE%
echo.

:: Get server IP
set /p SERVER_IP="Enter server IP address (e.g., 192.168.1.100): "
if "%SERVER_IP%"=="" (
    echo [ERROR] Server IP is required
    pause
    exit /b 1
)

:: Get employee ID
set /p EMP_ID="Enter employee ID (e.g., emp001): "
if "%EMP_ID%"=="" (
    echo [ERROR] Employee ID is required
    pause
    exit /b 1
)

:: Get employee name
set /p EMP_NAME="Enter employee name (e.g., John Doe): "

:: Get department
set /p DEPT="Enter department (e.g., Engineering): "

echo.
echo Updating configuration...

:: Use PowerShell to update the Python file
powershell -Command "(Get-Content '%CONFIG_FILE%') -replace '\"SERVER_URL\": \"http://[^\"]+\"', '\"SERVER_URL\": \"http://%SERVER_IP%:5601\"' | Set-Content '%CONFIG_FILE%'"
powershell -Command "(Get-Content '%CONFIG_FILE%') -replace '\"EMPLOYEE_ID\": \"[^\"]+\"', '\"EMPLOYEE_ID\": \"%EMP_ID%\"' | Set-Content '%CONFIG_FILE%'"
powershell -Command "(Get-Content '%CONFIG_FILE%') -replace '\"EMPLOYEE_NAME\": \"[^\"]*\"', '\"EMPLOYEE_NAME\": \"%EMP_NAME%\"' | Set-Content '%CONFIG_FILE%'"
powershell -Command "(Get-Content '%CONFIG_FILE%') -replace '\"DEPARTMENT\": \"[^\"]*\"', '\"DEPARTMENT\": \"%DEPT%\"' | Set-Content '%CONFIG_FILE%'"

echo.
echo [OK] Configuration updated!
echo.
echo New settings:
echo   Server: http://%SERVER_IP%:5601
echo   Employee ID: %EMP_ID%
echo   Employee Name: %EMP_NAME%
echo   Department: %DEPT%
echo.
echo You can now start the watcher.
echo.
pause
