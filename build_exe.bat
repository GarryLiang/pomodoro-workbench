@echo off
rem ============================================================
rem  Pomodoro Workbench - build a standalone exe with PyInstaller
rem  Output: dist\PomodoroWorkbench.exe  (no Python needed to run)
rem ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Build exe - Pomodoro Workbench

rem ---- locate python (same rules as start.bat) ----
set "PYEXE="
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo %%i | findstr /i "WindowsApps" >nul
    if errorlevel 1 if not defined PYEXE set "PYEXE=%%i"
)
if defined PYEXE (
    "!PYEXE!" -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>nul
    if errorlevel 1 set "PYEXE="
)
if not defined PYEXE (
    for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
        if exist "%%i" set "PYEXE=%%i"
    )
)
if not defined PYEXE goto :no_python

echo [OK] Python: !PYEXE!
echo [..] Installing PyInstaller (first run only)...
"!PYEXE!" -m pip install --upgrade pyinstaller >nul
if errorlevel 1 (
    echo [X] Failed to install PyInstaller. Check network access.
    goto :end
)

echo [..] Building single-file windowed exe...
"!PYEXE!" -m PyInstaller --noconfirm --clean -F -w -n PomodoroWorkbench main.py
if errorlevel 1 goto :end

echo.
echo [OK] Done! Run the app with:  dist\PomodoroWorkbench.exe
echo     You may copy that single exe to any Windows PC.
goto :end

:no_python
echo [X] Python not found. Run start.bat first so Python is installed.

:end
echo.
pause >nul
endlocal
