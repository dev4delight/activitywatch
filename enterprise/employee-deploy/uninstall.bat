@echo off
title ActivityWatch Uninstaller
color 0C

echo ============================================================
echo   ActivityWatch Employee Uninstaller
echo ============================================================
echo.

set INSTALL_DIR=%LOCALAPPDATA%\ActivityWatch-Employee
set STARTUP_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ActivityWatch.lnk
set DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\ActivityWatch.lnk

echo This will remove ActivityWatch from this computer.
echo.
set /p CONFIRM="Are you sure you want to uninstall? (Y/N): "
if /I not "%CONFIRM%"=="Y" (
    echo Uninstall cancelled.
    pause
    exit /b 0
)

echo.
echo Removing files...

:: Kill running watcher
taskkill /f /im python.exe /fi "WINDOWTITLE eq *aw_employee*" >nul 2>&1
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq *aw_employee*" >nul 2>&1

:: Remove shortcuts
if exist "%STARTUP_SHORTCUT%" del "%STARTUP_SHORTCUT%"
echo [OK] Startup shortcut removed

if exist "%DESKTOP_SHORTCUT%" del "%DESKTOP_SHORTCUT%"
echo [OK] Desktop shortcut removed

:: Remove installation directory
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo [OK] Installation directory removed
)

echo.
echo ============================================================
echo   UNINSTALL COMPLETE
echo ============================================================
echo.
echo ActivityWatch has been removed from this computer.
echo.
pause
