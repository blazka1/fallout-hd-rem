$ErrorActionPreference='Stop'
$project=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime=Join-Path $PSScriptRoot 'runtime'
$mask=Join-Path $runtime 'data/art/hd/player-male-vault13/walk-d3-f004.shadow-mask'
if(Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue){throw 'Close Fallout before testing.'}
$bytes=[IO.File]::ReadAllBytes($mask)
$previous=[Environment]::GetEnvironmentVariable('FALLOUT_HD_PLAYER_EXPECT_SHADOWS','Process')
try {
    $damaged=[byte[]]$bytes.Clone();$damaged[0]=255
    [IO.File]::WriteAllBytes($mask,$damaged)
    $env:FALLOUT_HD_PLAYER_EXPECT_SHADOWS='53'
    & (Join-Path $project 'work/hd-player-male/tools/test-player.ps1') -ProjectRoot $project -RuntimeDirectory $runtime -OutputDirectory (Join-Path $project 'build/hd-player-lighting-20261116/corrupt-shadow')
} finally {
    [IO.File]::WriteAllBytes($mask,$bytes)
    [Environment]::SetEnvironmentVariable('FALLOUT_HD_PLAYER_EXPECT_SHADOWS',$previous,'Process')
}
