@echo off
if not exist "%~dp0runtime\hd-world-pilot\fallout-ce.exe" (
    echo Run work\hd-world-pilot\tools\build.ps1 and prepare-runtime.ps1 first.
    pause
    exit /b 1
)
cd /d "%~dp0runtime\hd-world-pilot"
start "" "fallout-ce.exe" "[remaster]borderless=0"
