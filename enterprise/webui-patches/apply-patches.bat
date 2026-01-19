@echo off
echo ============================================================
echo   ActivityWatch WebUI Enterprise Patches
echo ============================================================
echo.

set WEBUI_DIR=%1

if "%WEBUI_DIR%"=="" (
    echo Usage: apply-patches.bat [path-to-aw-webui]
    echo.
    echo Example: apply-patches.bat C:\activitywatch\aw-webui
    exit /b 1
)

if not exist "%WEBUI_DIR%" (
    echo [ERROR] Directory not found: %WEBUI_DIR%
    exit /b 1
)

echo Applying patches to: %WEBUI_DIR%
echo.

:: Copy dist files (pre-built)
if not exist "%WEBUI_DIR%\dist\js" mkdir "%WEBUI_DIR%\dist\js"
copy /Y "%~dp0employee-selector.js" "%WEBUI_DIR%\dist\js\" >nul
echo [OK] Copied employee-selector.js to dist/js/

copy /Y "%~dp0index.html" "%WEBUI_DIR%\dist\" >nul
echo [OK] Copied index.html to dist/

:: Copy source files (for rebuilding)
if exist "%~dp0src" (
    echo.
    echo Copying source patches...
    xcopy /Y /E /I "%~dp0src\components\*" "%WEBUI_DIR%\src\components\" >nul 2>&1
    xcopy /Y /E /I "%~dp0src\stores\*" "%WEBUI_DIR%\src\stores\" >nul 2>&1
    echo [OK] Copied source files (Header.vue, employees.ts)
)

echo.
echo ============================================================
echo   Patches applied successfully!
echo ============================================================
echo.
echo The employee selector will appear in Activity view.
echo.
