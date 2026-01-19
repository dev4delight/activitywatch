@echo off
title ActivityWatch Employee Installer
color 0A

echo ============================================================
echo   ActivityWatch Employee Installer
echo ============================================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [WARNING] Running without admin rights - some features may be limited
    echo.
)

:: Check Python installation
python --version >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

:: Install required packages
echo Installing required Python packages...
pip install requests pywin32 psutil --quiet
if %errorLevel% NEQ 0 (
    echo [ERROR] Failed to install packages
    pause
    exit /b 1
)
echo [OK] Packages installed
echo.

:: Create installation directory
set INSTALL_DIR=%LOCALAPPDATA%\ActivityWatch-Employee
echo Creating installation directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy watcher script
echo Copying watcher script...
copy /Y "aw_employee_watcher.py" "%INSTALL_DIR%\" >nul
copy /Y "config.txt" "%INSTALL_DIR%\" >nul 2>&1
echo [OK] Files copied
echo.

:: Create startup shortcut
echo Creating startup shortcut...
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_FILE=%TEMP%\create_shortcut.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = "%STARTUP_DIR%\ActivityWatch.lnk" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"
echo oLink.TargetPath = "pythonw" >> "%VBS_FILE%"
echo oLink.Arguments = """%INSTALL_DIR%\aw_employee_watcher.py""" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_FILE%"
echo oLink.Description = "ActivityWatch Employee Watcher" >> "%VBS_FILE%"
echo oLink.Save >> "%VBS_FILE%"

cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%"
echo [OK] Startup shortcut created
echo.

:: Create desktop shortcut
echo Creating desktop shortcut...
set DESKTOP_DIR=%USERPROFILE%\Desktop
set VBS_FILE=%TEMP%\create_shortcut2.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = "%DESKTOP_DIR%\ActivityWatch.lnk" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"
echo oLink.TargetPath = "python" >> "%VBS_FILE%"
echo oLink.Arguments = """%INSTALL_DIR%\aw_employee_watcher.py""" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_FILE%"
echo oLink.Description = "Start ActivityWatch Watcher" >> "%VBS_FILE%"
echo oLink.Save >> "%VBS_FILE%"

cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%"
echo [OK] Desktop shortcut created
echo.

echo ============================================================
echo   INSTALLATION COMPLETE
echo ============================================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo IMPORTANT: Before running, edit the configuration in:
echo   %INSTALL_DIR%\aw_employee_watcher.py
echo.
echo Change these values:
echo   - SERVER_URL: Your server's IP address (e.g., http://192.168.1.100:5601)
echo   - EMPLOYEE_ID: Unique ID for this employee
echo   - EMPLOYEE_NAME: Employee's full name
echo   - DEPARTMENT: Department name
echo.
echo The watcher will start automatically on next login.
echo To start now, double-click the ActivityWatch shortcut on desktop.
echo.
pause
