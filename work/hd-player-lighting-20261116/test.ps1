param([string]$Version='v1')
$ErrorActionPreference='Stop'
$project=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime=Join-Path $PSScriptRoot 'runtime'
if(Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue){throw 'Close the running Fallout before testing.'}
$package=Join-Path $project 'assets/hd/player-male-vault13/lighting-v2-x4'
$dest=Join-Path $runtime 'data/art/hd/player-male-vault13'
$manifest=Get-Content (Join-Path $package 'manifest.json') -Raw | ConvertFrom-Json
foreach($entry in $manifest.entries){
    foreach($name in @($entry.filename,$entry.png,$entry.shadow_mask)){
        Copy-Item -LiteralPath (Join-Path $package $name) -Destination (Join-Path $dest $name) -Force
    }
}
Copy-Item -LiteralPath (Join-Path $package 'registry.tsv'),(Join-Path $package 'manifest.json') -Destination $dest -Force
$exe=Join-Path $project 'build/hd-player-lighting-20261116/msvc/RelWithDebInfo/fallout-ce.exe'
Copy-Item -LiteralPath $exe -Destination (Join-Path $runtime 'fallout-ce.exe') -Force
& (Join-Path $project 'work/hd-player-male/tools/test-player.ps1') -ProjectRoot $project -RuntimeDirectory $runtime -OutputDirectory (Join-Path $project ('build/hd-player-lighting-20261116/'+$Version))
