@echo off
rem ============================================================
rem  Pomodoro Workbench - One-click launcher (Windows)
rem  Detect Python 3.10+ (with tkinter), auto-install when
rem  missing, then start the app. No third-party packages.
rem ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Pomodoro Workbench

echo ============================================
echo   Pomodoro Workbench - One-Click Start
echo ============================================
echo.

rem ---------- 1. resolve the path of a usable Python ----------
set "PYEXE="

rem 1a. real python.exe on PATH (skip Microsoft Store alias)
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo %%i | findstr /i "WindowsApps" >nul
    if errorlevel 1 if not defined PYEXE set "PYEXE=%%i"
)
if defined PYEXE (
    "!PYEXE!" -c "import sys,tkinter;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if errorlevel 1 set "PYEXE="
)

rem 1b. python launcher (py -3) -> resolve its real python path
if not defined PYEXE (
    for /f "delims=" %%i in ('py -3 -c "import sys,tkinter;print(sys.executable)" 2^>nul') do (
        if exist "%%i" set "PYEXE=%%i"
    )
)

rem 1c. official per-user installs (Python3.10 .. Python3.13)
if not defined PYEXE (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%~d\python.exe" (
            "%%~d\python.exe" -c "import sys,tkinter;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYEXE=%%~d\python.exe"
        )
    )
)

rem ---------- 2. run, or auto-install Python first ----------
if not defined PYEXE goto :install_python

echo [OK] Python found: !PYEXE!
echo [OK] Starting Pomodoro Workbench...
echo.
"!PYEXE!" main.py
goto :end

:install_python
echo [..] No usable Python 3.10+ found. Trying winget auto-install...
where winget >nul 2>nul
if errorlevel 1 (
    echo.
    echo [X] winget not available. Please install Python manually:
    echo     https://www.python.org/downloads/
    echo     Check "Add python.exe to PATH" during installation,
    echo     then run this script again.
    goto :end
)
echo [..] Installing Python 3.12 for current user (silent)...
winget install --id Python.Python.3.12 -e --scope user --silent ^
    --accept-package-agreements --accept-source-agreements --disable-interactivity

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo [OK] Python installed. Starting Pomodoro Workbench...
    echo.
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py
) else (
    echo.
    echo [X] Automatic install did not finish. Please run this script
    echo     once more, or install Python from https://www.python.org/
)

:end
echo.
echo ------------------------------------------------------------
echo   Exited. Close this window or press any key to continue...
echo ------------------------------------------------------------
pause >nul
endlocal
