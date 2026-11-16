param([string]$Version = 'v1')
$ErrorActionPreference = 'Stop'
$project = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime = Join-Path $PSScriptRoot 'runtime'
$exe = Join-Path $project 'build/hd-player-shadow-20261116/msvc/RelWithDebInfo/fallout-ce.exe'
if (Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue) { throw 'Close the running Fallout before testing.' }
Copy-Item -LiteralPath $exe -Destination (Join-Path $runtime 'fallout-ce.exe') -Force
& (Join-Path $project 'work/hd-player-male/tools/test-player.ps1') -ProjectRoot $project -RuntimeDirectory $runtime -OutputDirectory (Join-Path $project ('build/hd-player-shadow-20261116/' + $Version))
