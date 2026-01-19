@echo off
title ActivityWatch Employee Setup
color 0A

echo ============================================================
echo   ActivityWatch Employee Quick Setup
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
echo [OK] Python found

:: Install packages
echo.
echo Installing required packages...
pip install requests pywin32 psutil --quiet
echo [OK] Packages installed

:: Get configuration
echo.
echo ============================================================
echo   Configuration
echo ============================================================
set /p SERVER_IP="Enter server IP address: "
set /p EMP_ID="Enter your employee ID: "
set /p EMP_NAME="Enter your name: "
set /p DEPT="Enter department: "

:: Update the watcher script
echo.
echo Configuring watcher...
powershell -Command "(Get-Content 'aw_employee_watcher.py') -replace '\"SERVER_URL\": \"http://[^\"]+\"', '\"SERVER_URL\": \"http://%SERVER_IP%:5601\"' | Set-Content 'aw_employee_watcher.py'"
powershell -Command "(Get-Content 'aw_employee_watcher.py') -replace '\"EMPLOYEE_ID\": \"[^\"]+\"', '\"EMPLOYEE_ID\": \"%EMP_ID%\"' | Set-Content 'aw_employee_watcher.py'"
powershell -Command "(Get-Content 'aw_employee_watcher.py') -replace '\"EMPLOYEE_NAME\": \"[^\"]*\"', '\"EMPLOYEE_NAME\": \"%EMP_NAME%\"' | Set-Content 'aw_employee_watcher.py'"
powershell -Command "(Get-Content 'aw_employee_watcher.py') -replace '\"DEPARTMENT\": \"[^\"]*\"', '\"DEPARTMENT\": \"%DEPT%\"' | Set-Content 'aw_employee_watcher.py'"

:: Test connection
echo.
echo Testing connection to server...
python -c "import requests; r=requests.get('http://%SERVER_IP%:5601/api/0/info', timeout=5); print('[OK] Connected to server' if r.status_code==200 else '[ERROR] Server error')" 2>nul
if %errorLevel% NEQ 0 (
    echo [WARNING] Could not connect to server. Check if server is running.
)

:: Create startup shortcut
echo.
echo Creating startup shortcut...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo Set ws = CreateObject("WScript.Shell") > "%TEMP%\sc.vbs"
echo Set link = ws.CreateShortcut("%STARTUP%\ActivityWatch.lnk") >> "%TEMP%\sc.vbs"
echo link.TargetPath = "pythonw" >> "%TEMP%\sc.vbs"
echo link.Arguments = """%CD%\aw_employee_watcher.py""" >> "%TEMP%\sc.vbs"
echo link.WorkingDirectory = "%CD%" >> "%TEMP%\sc.vbs"
echo link.Save >> "%TEMP%\sc.vbs"
cscript //nologo "%TEMP%\sc.vbs"
del "%TEMP%\sc.vbs"
echo [OK] Will start automatically on login

:: Start now
echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Server: http://%SERVER_IP%:5601
echo Employee: %EMP_NAME% (%EMP_ID%)
echo.
set /p START_NOW="Start tracking now? (Y/N): "
if /I "%START_NOW%"=="Y" (
    echo Starting ActivityWatch...
    start "" pythonw aw_employee_watcher.py
    echo [OK] ActivityWatch is now running in the background
)
echo.
pause
