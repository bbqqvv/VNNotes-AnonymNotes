@echo off
title Stealth Assist Installer
color 0A

echo ==================================================
echo       STEALTH ASSIST INSTALLATION
echo ==================================================
echo.

:: 1. Define Source and Destination
set "CURRENT_DIR=%~dp0"
set "SOURCE_DIR=%CURRENT_DIR%dist\StealthAssist"
set "INSTALL_DIR=%LOCALAPPDATA%\StealthAssist"
set "EXE_PATH=%INSTALL_DIR%\StealthAssist.exe"

:: 2. Check source
if not exist "%SOURCE_DIR%" (
    color 0C
    echo [ERROR] Could not find application files in:
    echo %SOURCE_DIR%
    echo.
    echo Please make sure you have built the app using PyInstaller properly.
    pause
    exit /b
)

:: 3. Copy Files
echo [*] Installing to: %INSTALL_DIR%
if exist "%INSTALL_DIR%" (
    echo     - Cleaning old version...
    rmdir /S /Q "%INSTALL_DIR%"
)

echo     - Copying files...
mkdir "%INSTALL_DIR%"
xcopy /E /Q /Y "%SOURCE_DIR%\*" "%INSTALL_DIR%\" >nul

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Failed to copy files.
    pause
    exit /b
)

:: 4. Create Shortcut
echo [*] Creating Desktop Shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Stealth Assist.lnk"
set "PWS_CMD=$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%EXE_PATH%';$s.WorkingDirectory='%INSTALL_DIR%';$s.IconLocation='%EXE_PATH%';$s.Save()"

powershell -Command "%PWS_CMD%"

echo.
echo ==================================================
echo    INSTALLATION SUCCESSFUL!
echo ==================================================
echo.
echo You can now find 'Stealth Assist' on your Desktop.
echo.
pause
