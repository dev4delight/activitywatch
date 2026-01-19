@echo off
:: Silent installer for automated deployment
:: Usage: silent_install.bat SERVER_IP EMPLOYEE_ID EMPLOYEE_NAME DEPARTMENT

set SERVER_IP=%1
set EMP_ID=%2
set EMP_NAME=%3
set DEPT=%4

if "%SERVER_IP%"=="" (
    echo Usage: silent_install.bat SERVER_IP EMPLOYEE_ID EMPLOYEE_NAME DEPARTMENT
    exit /b 1
)
if "%EMP_ID%"=="" (
    echo Usage: silent_install.bat SERVER_IP EMPLOYEE_ID EMPLOYEE_NAME DEPARTMENT
    exit /b 1
)

:: Install packages silently
pip install requests pywin32 psutil --quiet 2>nul

:: Create installation directory
set INSTALL_DIR=%LOCALAPPDATA%\ActivityWatch-Employee
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy and configure watcher
copy /Y "%~dp0aw_employee_watcher.py" "%INSTALL_DIR%\" >nul

:: Update configuration
powershell -Command "(Get-Content '%INSTALL_DIR%\aw_employee_watcher.py') -replace '\"SERVER_URL\": \"http://[^\"]+\"', '\"SERVER_URL\": \"http://%SERVER_IP%:5601\"' | Set-Content '%INSTALL_DIR%\aw_employee_watcher.py'"
powershell -Command "(Get-Content '%INSTALL_DIR%\aw_employee_watcher.py') -replace '\"EMPLOYEE_ID\": \"[^\"]+\"', '\"EMPLOYEE_ID\": \"%EMP_ID%\"' | Set-Content '%INSTALL_DIR%\aw_employee_watcher.py'"
if not "%EMP_NAME%"=="" powershell -Command "(Get-Content '%INSTALL_DIR%\aw_employee_watcher.py') -replace '\"EMPLOYEE_NAME\": \"[^\"]*\"', '\"EMPLOYEE_NAME\": \"%EMP_NAME%\"' | Set-Content '%INSTALL_DIR%\aw_employee_watcher.py'"
if not "%DEPT%"=="" powershell -Command "(Get-Content '%INSTALL_DIR%\aw_employee_watcher.py') -replace '\"DEPARTMENT\": \"[^\"]*\"', '\"DEPARTMENT\": \"%DEPT%\"' | Set-Content '%INSTALL_DIR%\aw_employee_watcher.py'"

:: Create startup shortcut
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\cs.vbs"
echo Set oLink = oWS.CreateShortcut("%STARTUP_DIR%\ActivityWatch.lnk") >> "%TEMP%\cs.vbs"
echo oLink.TargetPath = "pythonw" >> "%TEMP%\cs.vbs"
echo oLink.Arguments = """%INSTALL_DIR%\aw_employee_watcher.py""" >> "%TEMP%\cs.vbs"
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%TEMP%\cs.vbs"
echo oLink.Save >> "%TEMP%\cs.vbs"
cscript //nologo "%TEMP%\cs.vbs"
del "%TEMP%\cs.vbs"

:: Start watcher
start "" pythonw "%INSTALL_DIR%\aw_employee_watcher.py"

echo Installation complete for %EMP_ID%
