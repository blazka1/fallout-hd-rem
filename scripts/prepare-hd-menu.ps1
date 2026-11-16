[CmdletBinding()]
param([string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-menu'
$gameData = Join-Path $projectPath 'FALLOUT (extract.me)'
$executable = Join-Path $projectPath 'build/fallout1-ce/RelWithDebInfo/fallout-ce.exe'
$portraitPng = Join-Path $projectPath 'assets/hd/main-menu/menu-portrait-v1.png'
$buttonSource = Join-Path $projectPath 'assets/hd/main-menu/buttons/new-game/v2'
foreach ($required in @($executable, $portraitPng, (Join-Path $gameData 'MASTER.DAT'), (Join-Path $gameData 'CRITTER.DAT'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing: $required" }
}
New-Item -ItemType Directory -Path (Join-Path $runtime 'data') -Force | Out-Null
$artDirectory = Join-Path $runtime 'data/art/hd/main-menu'
New-Item -ItemType Directory -Path $artDirectory -Force | Out-Null
# Format conversion only: no scaling, retouching, palette reduction, or new model run.
Add-Type -AssemblyName System.Drawing
$portrait = [System.Drawing.Image]::FromFile($portraitPng)
try {
    if ($portrait.Width -ne 1800 -or $portrait.Height -ne 2160) {
        throw 'Expected the selected 1800x2160 portrait PNG.'
    }
    $portrait.Save((Join-Path $artDirectory 'menu-portrait-v1.bmp'), [System.Drawing.Imaging.ImageFormat]::Bmp)
} finally {
    $portrait.Dispose()
}
$buttonDirectory = Join-Path $artDirectory 'new-game'
New-Item -ItemType Directory -Path $buttonDirectory -Force | Out-Null
foreach ($state in @('normal', 'hover', 'pressed')) {
    $image = [System.Drawing.Image]::FromFile((Join-Path $buttonSource "$state.png"))
    try {
        if ($image.Width -ne 1020 -or $image.Height -ne 152) {
            throw "Expected a 1020x152 New Game $state PNG."
        }
        $image.Save((Join-Path $buttonDirectory "$state.bmp"), [System.Drawing.Imaging.ImageFormat]::Bmp)
    } finally {
        $image.Dispose()
    }
}
Copy-Item -LiteralPath $executable -Destination (Join-Path $runtime 'fallout-ce.exe') -Force
$config = Join-Path $runtime 'fallout.cfg'
if (-not (Test-Path -LiteralPath $config)) {
    @"
[system]
master_dat=$gameData\MASTER.DAT
critter_dat=$gameData\CRITTER.DAT
master_patches=data
critter_patches=data
language=english
art_cache_size=64

[sound]
music_path1=$gameData\DATA\SOUND\MUSIC\
music_path2=$gameData\DATA\SOUND\MUSIC\

[preferences]
subtitles=1

[remaster]
hd_main_menu=1
hd_background=1
hd_menu_buttons=1
skip_intro=1
borderless=1
"@ | Set-Content -LiteralPath $config -Encoding ascii
}
$resolution = Join-Path $runtime 'f1_res.ini'
if (-not (Test-Path -LiteralPath $resolution)) {
    @'
[MAIN]
SCR_WIDTH=1920
SCR_HEIGHT=1080
WINDOWED=1
SCALE_2X=1
'@ | Set-Content -LiteralPath $resolution -Encoding ascii
}
Write-Output "HD menu ready: $runtime"

