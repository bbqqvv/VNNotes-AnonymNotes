@echo off
title VNNotes Factory Reset
color 0c

echo ==========================================================
echo                 VNNOTES FACTORY RESET                     
echo ==========================================================
echo.
echo WARNING: This action is IRREVERSIBLE.
echo It will permanently delete ALL your notes, settings,
echo saved layouts, and application cache.
echo.
echo Your VNNotes application will be returned to a "like new" state.
echo.

set /p CONFIRM="Type 'YES' to confirm and delete all data: "

if /i "%CONFIRM%" neq "YES" (
    echo.
    echo Reset aborted. Your data is safe.
    pause
    exit /b
)

echo.
echo [1/2] Locating and deleting application data...
if exist "%APPDATA%\vtechdigitalsolution" (
    rmdir /s /q "%APPDATA%\vtechdigitalsolution"
    echo  - Application data wiped successfully.
) else (
    echo  - No application data found. (Already clean)
)

echo [2/2] Locating and deleting local cache...
if exist "%LOCALAPPDATA%\vtechdigitalsolution" (
    rmdir /s /q "%LOCALAPPDATA%\vtechdigitalsolution"
    echo  - Local cache wiped successfully.
) else (
    echo  - No local cache found. (Already clean)
)

echo.
echo ==========================================================
echo RESET SUCCESSFUL
echo ==========================================================
echo VNNotes has been completely wiped and reset.
echo You may now open the application as a fresh install.
pause
