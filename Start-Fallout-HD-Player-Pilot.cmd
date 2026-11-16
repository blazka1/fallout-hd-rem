@echo off
setlocal
if not exist "%~dp0runtime\hd-world-pilot\fallout-ce.exe" (
    echo Build and install the HD player pilot first.
    pause
    exit /b 1
)
set "FALLOUT_HD_PLAYER_DEMO=1"
set "FALLOUT_HD_PLAYER_PREVIEW="
set "FALLOUT_HD_WORLD_PREVIEW="
set "FALLOUT_HD_MENU_PREVIEW="
cd /d "%~dp0runtime\hd-world-pilot"
start "" "fallout-ce.exe" "[remaster]borderless=0"
endlocal
