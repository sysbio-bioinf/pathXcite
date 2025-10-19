@echo off
setlocal
REM Double-click launcher for the GUI setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_win_3_3.ps1"
