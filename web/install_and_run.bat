@echo off
echo Installing dependencies...
call npm install --legacy-peer-deps
echo.
echo Starting development server...
call npm run dev
pause
