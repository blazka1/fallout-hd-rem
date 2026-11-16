[CmdletBinding()]
param(
    [string]$OutputDirectory = 'build/hd-rat-20261115/preview/loaded',
    [int]$ExpectedKeys = 540,
    [ValidateSet(-1,0,1)][int]$ExpectedAimed = -1,
    [ValidateRange(30,1800)][int]$TimeoutSeconds = 900
)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime = Join-Path $projectPath 'runtime/hd-rat-pilot'
$exe = Join-Path $runtime 'fallout-ce.exe'
$output = [IO.Path]::GetFullPath((Join-Path $projectPath $OutputDirectory))
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) { throw 'Another Fallout instance is running; it was preserved.' }
if (Test-Path -LiteralPath (Join-Path $output 'result.json')) { throw 'Retain existing report; select a fresh output directory.' }
foreach ($path in @('data/maps/V13ENT.SAV','data/maps/V13ENT.MAP','maps/V13ENT.SAV','maps/V13ENT.MAP')) {
    if(Test-Path -LiteralPath (Join-Path $runtime $path)) { throw "Saved/local map override present: $path" }
}
New-Item -ItemType Directory -Force -Path $output | Out-Null
$names = @('FALLOUT_HD_RAT_PREVIEW','FALLOUT_HD_RAT_EXPECT_KEYS','FALLOUT_HD_RAT_EXPECT_AIMED','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_PLAYER_DEMO')
$old = @{};foreach($name in $names) { $old[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$null,'Process') }
$config = Join-Path $runtime 'fallout.cfg';$configBytes=[IO.File]::ReadAllBytes($config)
try {
    $env:FALLOUT_HD_RAT_PREVIEW=$output;$env:FALLOUT_HD_RAT_EXPECT_KEYS=[string]$ExpectedKeys
    if($ExpectedAimed -ge 0) { $env:FALLOUT_HD_RAT_EXPECT_AIMED=[string]$ExpectedAimed }
    $process=Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while(-not $process.WaitForExit(1000)) {
        if($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {Stop-Process -Id $process.Id -Force;throw 'Own rat preview exceeded timeout.'}
    }
    $process.Refresh()
    Add-Type -AssemblyName System.Drawing
    foreach($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $image=[Drawing.Image]::FromFile($bmp.FullName)
        try {$image.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png)} finally {$image.Dispose()}
    }
    $result=Get-Content -LiteralPath (Join-Path $output 'result.json') -Raw | ConvertFrom-Json
    [ordered]@{created_utc=[DateTime]::UtcNow.ToString('o');executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash;exit_code=$process.ExitCode;result=$result} |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    $result | ConvertTo-Json -Compress
    if($process.ExitCode -ne 0 -or $result.failed -ne 0) {Get-Content -LiteralPath (Join-Path $output 'checks.txt') | Select-String '^FAIL';throw 'Rat preview failed.'}
} finally {
    [IO.File]::WriteAllBytes($config,$configBytes)
    foreach($name in $names) {[Environment]::SetEnvironmentVariable($name,$old[$name],'Process')}
}
