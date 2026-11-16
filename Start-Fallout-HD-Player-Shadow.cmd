@echo off
setlocal
if not exist "%~dp0work\hd-player-shadow-20261116\runtime\fallout-ce.exe" (
    echo Build the isolated player shadow trial first.
    pause
    exit /b 1
)
set "FALLOUT_HD_PLAYER_DEMO=1"
set "FALLOUT_HD_PLAYER_PREVIEW="
set "FALLOUT_HD_WORLD_PREVIEW="
set "FALLOUT_HD_MENU_PREVIEW="
cd /d "%~dp0work\hd-player-shadow-20261116\runtime"
start "" "fallout-ce.exe" "[remaster]borderless=0" "[remaster]hd_player_shadow=1"
endlocal
