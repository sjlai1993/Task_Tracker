@echo off
title Building TaskTracker Executable

echo ========================================
echo   Building TaskTracker with PyInstaller
echo ========================================
echo.

REM Run PyInstaller using the spec file
pyinstaller TaskTracker.spec

echo.
echo ==========================================================
echo Build process finished.
echo The executable can be found in the 'dist\TaskTracker' folder.
echo ==========================================================
echo.
pause