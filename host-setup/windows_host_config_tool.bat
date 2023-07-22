@echo off

:MainMenu
cls
echo =====================================
echo  Windows Host Configuration Tool
echo =====================================
echo.
echo Choose an option:
echo 1. Install Windows Host Configurations and API Controller settings.
echo 2. Uninstall Windows Host Configurations and revert to default.
echo 3. Check Status of Changes
echo 4. Exit

set /p choice=Enter option number: 

if "%choice%"=="1" (
    echo Installing Windows Host Configurations and API Controller settings...
    PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-host.ps1" >> install-log.txt 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo An error occurred during installation. Please check the install-log.txt for details.
    ) else (
        echo Installation completed successfully.
    )
    pause
    goto MainMenu
)

if "%choice%"=="2" (
    echo Uninstalling Windows Host Configurations and reverting to default...
    PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-host.ps1" >> uninstall-log.txt 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo An error occurred during uninstallation. Please check the uninstall-log.txt for details.
    ) else (
        echo Uninstallation completed successfully.
    )
    pause
    goto MainMenu
)

if "%choice%"=="3" (
    echo Checking status of changes...
    PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0host-checker.ps1" >> status-log.txt 2>&1
    pause
    goto MainMenu
)

if "%choice%"=="4" (
    echo Exiting...
    exit /b
)

echo Invalid choice. Please try again.
pause
goto MainMenu
