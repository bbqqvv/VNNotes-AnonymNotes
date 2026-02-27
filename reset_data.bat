@echo off
setlocal enabledelayedexpansion
title VNNotes Global Reset Utility v2.1
color 0b

:: VNNotes Factory Reset Script v2.1
:: This script performs a destructive wipe of ALL application data with VERIFICATION.

echo ==========================================================
echo               VNNOTES GLOBAL FACTORY RESET               
echo ==========================================================
echo.
echo [!] WARNING: This action is PERMANENT and IRREVERSIBLE.
echo.
echo This utility will delete:
echo  1. All Notes and the SQLite Database
echo  2. Application Settings and UI Layouts
echo  3. Log files and Crash reports
echo  4. Local Cache and Temporary browser data (QtWebEngine)
echo.
echo ==========================================================
echo.

set /p CONFIRM="Type 'YES' to proceed with the total wipe: "

if /i "%CONFIRM%" neq "YES" (
    echo.
    echo Reset sequence aborted. No files were harmed.
    pause
    exit /b
)

echo.
echo [!] STARTING RESET SEQUENCE...
echo.

:: 1. Process Termination
echo [1/6] Terminating all related processes...
taskkill /f /im python.exe /fi "WINDOWTITLE eq VNNotes*" >nul 2>&1
taskkill /f /im VNNotes.exe >nul 2>&1
taskkill /f /im QtWebEngineProcess.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo      - Processes cleared.

:: 2. App Data Cleanup (Database & Settings)
echo [2/6] Wiping Application Data (vtechdigitalsolution)...
if exist "%APPDATA%\vtechdigitalsolution" (
    rmdir /s /q "%APPDATA%\vtechdigitalsolution"
)

:: 3. Log Directory Cleanup
echo [3/6] Cleaning Logs (VNNotes)...
if exist "%APPDATA%\VNNotes" (
    rmdir /s /q "%APPDATA%\VNNotes"
)

:: 4. Local Cache Cleanup
echo [4/6] Clearing Local Cache...
if exist "%LOCALAPPDATA%\vtechdigitalsolution" (
    rmdir /s /q "%LOCALAPPDATA%\vtechdigitalsolution"
)
if exist "%LOCALAPPDATA%\VNNotes" (
    rmdir /s /q "%LOCALAPPDATA%\VNNotes"
)

:: 5. Local Project Cleanup
echo [5/6] Removing local crash logs and trace files...
if exist "FATAL_CRASH.txt" del /f /q "FATAL_CRASH.txt"
if exist "debug.log" del /f /q "debug.log"
if exist "trace.log" del /f /q "trace.log"
if exist "*.migrated" del /f /q "*.migrated"

:: 6. Verification
echo [6/6] Verifying wipe success...
set FAILED=0
if exist "%APPDATA%\vtechdigitalsolution" set FAILED=1
if exist "%APPDATA%\VNNotes" set FAILED=1
if exist "%LOCALAPPDATA%\vtechdigitalsolution" set FAILED=1

if %FAILED%==1 (
    color 0c
    echo.
    echo [!!!] ERROR: Some files could not be deleted.
    echo [!!!] Please ensure VNNotes is CLOSED and try again.
    echo [!!!] You may need to restart your computer if a process is hanging.
) else (
    echo.
    echo ==========================================================
    echo                  RESET SUCCESSFUL
    echo ==========================================================
    echo.
    echo VNNotes has been completely restored to factory defaults.
    echo All user-specific data has been purged.
)

echo.
pause
