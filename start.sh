#!/usr/bin/env sh
# ============================================================
#  Pomodoro Workbench - One-click launcher (Linux / macOS)
#  Uses Python 3.10+ with tkinter; no third-party packages.
# ============================================================
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  Pomodoro Workbench - One-Click Start"
echo "============================================"

PY=""
if command -v python3 >/dev/null 2>&1 &&
   python3 -c 'import sys,tkinter;sys.exit(0 if sys.version_info>=(3,10) else 1)' >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1 &&
     python -c 'import sys,tkinter;sys.exit(0 if sys.version_info>=(3,10) else 1)' >/dev/null 2>&1; then
    PY=python
fi

if [ -z "$PY" ]; then
    echo "[X] No usable Python 3.10+ with tkinter found."
    echo
    echo "    macOS :  brew install python-tk          (after installing Homebrew)"
    echo "    Ubuntu:  sudo apt install python3 python3-tk"
    echo "    Fedora:  sudo dnf install python3 tkinter"
    echo "    Then re-run:  ./start.sh"
    exit 1
fi

echo "[OK] Python found: $PY"
echo "[OK] Starting Pomodoro Workbench..."
echo
exec "$PY" main.py
