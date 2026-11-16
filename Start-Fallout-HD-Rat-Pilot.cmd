@echo off
setlocal
if not exist "%~dp0runtime\hd-rat-pilot\data\art\hd\critter-rat\registry.tsv" (
    echo The HD rat package is not installed in the isolated pilot yet.
    pause
    exit /b 1
)
set "FALLOUT_HD_PLAYER_DEMO=1"
set "FALLOUT_HD_RAT_PREVIEW="
set "FALLOUT_HD_PLAYER_PREVIEW="
set "FALLOUT_HD_WORLD_PREVIEW="
set "FALLOUT_HD_HUD_PREVIEW="
set "FALLOUT_HD_MENU_PREVIEW="
cd /d "%~dp0runtime\hd-rat-pilot"
start "" "fallout-ce.exe" "[remaster]borderless=0"
endlocal
