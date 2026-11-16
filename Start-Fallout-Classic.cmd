@echo off
cd /d "%~dp0runtime\classic"
if not exist "fallout-ce.exe" (
    echo Classic runtime is not prepared. Run scripts\prepare-classic.ps1 first.
    pause
    exit /b 1
)
start "" "fallout-ce.exe"
