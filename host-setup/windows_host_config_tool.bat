@echo off

:MainMenu
cls
echo =====================================
echo  Windows Host Configuration Tool
echo =====================================
echo.
echo Choose an option:
echo.
echo   1. Install Windows Host Configurations and API Controller settings.
echo   2. Uninstall Windows Host Configurations and revert to default.
echo   3. Check Status of Changes
echo.
for /f "usebackq delims=" %%i in (`powershell.exe -Command "Get-ExecutionPolicy"`) do (
    echo   Current ExecutionPolicy: %%i
)
echo   4. Set ExecutionPolicy to Unrestricted
echo   5. Set ExecutionPolicy to Restricted
echo.
echo   6. Reboot System
echo   7. Exit
echo.
set /p choice=Enter option number: 

rem Input validation
setlocal enabledelayedexpansion
set "valid_choices=1234567"
echo !valid_choices! | find "!choice!" > nul
if errorlevel 1 (
    echo Invalid choice. Please try again.
    pause
    goto MainMenu
)

if "%choice%"=="1" (
    echo.
    echo Installing Windows Host Configurations and API Controller settings...
    echo.
    PowerShell.exe -Command "%~dp0install-host.ps1"
    pause > nul
    goto MainMenu
)

if "%choice%"=="2" (
    echo.
    echo Uninstalling Windows Host Configurations and reverting to default...
    echo.
    PowerShell.exe -Command "%~dp0uninstall-host.ps1"
    pause > nul
    goto MainMenu
)

if "%choice%"=="3" (
    echo.
    echo Checking status of changes...
    echo.
    PowerShell.exe -Command "%~dp0check-host.ps1"
    pause > nul
    goto MainMenu
)

if "%choice%"=="4" (
    echo.
    echo Changine ExecutionPolicy to Unrestricted...
    echo.
	powershell.exe -Command "Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser"
	echo Press any key to continue...
    pause > nul
    goto MainMenu
)

if "%choice%"=="5" (
    echo.
    echo Changine ExecutionPolicy to Restricted...
    echo.
    PowerShell.exe -Command "Set-ExecutionPolicy -ExecutionPolicy Restricted -Scope CurrentUser"
	echo Press any key to continue...
    pause > nul
    goto MainMenu
)

if "%choice%"=="6" (
    echo.
    echo Restarting...
	shutdown /r /t 0
)

if "%choice%"=="7" (
    echo.
    echo Exiting...
    exit /b
)

goto MainMenu