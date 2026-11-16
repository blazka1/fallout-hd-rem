@echo off
cd /d "%~dp0runtime\hd-menu"
if not exist "fallout-ce.exe" (
    echo Run scripts\prepare-hd-menu.ps1 first.
    pause
    exit /b 1
)
start "" "fallout-ce.exe" "[remaster]borderless=0"
