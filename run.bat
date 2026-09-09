@echo off
rem 番茄工作台 启动脚本（Windows）
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 及以上版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python main.py
pause
