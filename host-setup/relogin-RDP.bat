:: ==========================================================================================
:: Script Name: Session Reconnection Script
:: Author: Andrew McDonald
:: Date: 24/02/2024
::
:: Description:
::     This script is designed to automatically reconnect remote sessions for the 'admin'
::     user that may have been disconnected. It logs all actions taken during the reconnection
::     process to a file specified by the 'logFile' variable.
::
::     The script operates by first logging the start of a reconnection attempt. It then uses
::     the 'query session' command to list all sessions and filters for those belonging to 'admin'.
::     For each session found, it attempts to reconnect the session using 'tscon.exe' and logs
::     the outcome of each reconnection attempt, whether successful or failed, along with the
::     session ID involved.
::
:: Usage:
::     This script is intended to be executed as a scheduled task in response to a disconnect event
::     for a remote session involving the 'admin' user. It ensures that the 'admin' user's sessions
::     are promptly reconnected, minimizing downtime and ensuring continued access.
::
:: Requirements:
::     - The script must be run with administrative privileges to successfully reconnect sessions.
::     - The scheduled task should be configured to trigger on disconnect events.
::
:: Log File:
::     The script outputs its logs to 'C:\Users\admin\Documents\debug_log.txt', including timestamps
::     for each action taken. This file should be regularly checked for errors or to verify successful
::     reconnections.
:: ==========================================================================================

@echo off
set logFile=C:\Users\admin\Documents\debug_log.txt

echo [%date% %time%] Starting session reconnection script. >> %logFile%
echo [%date% %time%] Attempting to reconnect any session for admin: >> %logFile%
query session | findstr /i "admin" >> %logFile%

for /f "tokens=2-4" %%a in ('query session ^| findstr /i "admin"') do (
    echo Attempting to reconnect session ID %%a for admin regardless of state. >> %logFile%
    tscon.exe %%a /dest:console >> %logFile% 2>&1
    if errorlevel 1 (
        echo Failed to reconnect session %%a. Check permissions and session ID. >> %logFile%
    ) else (
        echo Successfully reconnected session %%a to console. >> %logFile%
    )
)

echo [%date% %time%] Script execution completed. >> %logFile%
