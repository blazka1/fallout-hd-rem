[CmdletBinding()]
param(
    [ValidateSet('rat','world','menu','player','hud')][string]$Mode='rat',
    [string]$OutputDirectory='',
    [int]$ExpectedKeys=540,
    [int]$ExpectedAimed=1,
    [string]$Executable='',
    [int]$TimeoutSeconds=900
)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime=Join-Path $root 'runtime/hd-world-pilot'
$exe=Join-Path $runtime 'fallout-ce.exe'
if($Executable){$exe=(Resolve-Path -LiteralPath $Executable).Path}
if (Get-Process fallout-ce -ErrorAction SilentlyContinue) {throw 'Another Fallout instance is running; preserved.'}
if (-not $OutputDirectory) {$OutputDirectory="build/hd-rat-world-integration-20261115/$Mode"}
$output=[IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (Test-Path (Join-Path $output 'manifest.json')) {throw 'Retain existing report; choose a new directory.'}
foreach($p in @('data/maps/V13ENT.SAV','data/maps/V13ENT.MAP','maps/V13ENT.SAV','maps/V13ENT.MAP')) {
    if(Test-Path (Join-Path $runtime $p)) {throw "Map override present and preserved: $p"}
}
New-Item -ItemType Directory -Force $output | Out-Null
$names=@('FALLOUT_HD_RAT_PREVIEW','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_PLAYER_DEMO',
    'FALLOUT_HD_RAT_EXPECT_KEYS','FALLOUT_HD_RAT_EXPECT_AIMED','FALLOUT_HD_WORLD_EXPECT_COUNT','FALLOUT_HD_MENU_EXPECT_HD')
$old=@{};foreach($n in $names) {$old[$n]=[Environment]::GetEnvironmentVariable($n,'Process');[Environment]::SetEnvironmentVariable($n,$null,'Process')}
$cfg=Join-Path $runtime 'fallout.cfg';$cfgBytes=[IO.File]::ReadAllBytes($cfg)
$automap=Join-Path $runtime 'data/MAPS/AUTOMAP.DB'
$automapBytes=if(Test-Path -LiteralPath $automap){[IO.File]::ReadAllBytes($automap)}else{$null}
try {
    [Environment]::SetEnvironmentVariable("FALLOUT_HD_$($Mode.ToUpperInvariant())_PREVIEW",$output,'Process')
    $env:FALLOUT_HD_RAT_EXPECT_KEYS=[string]$ExpectedKeys;$env:FALLOUT_HD_RAT_EXPECT_AIMED=[string]$ExpectedAimed
    $env:FALLOUT_HD_WORLD_EXPECT_COUNT='247';$env:FALLOUT_HD_MENU_EXPECT_HD='1'
    $process=Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while(-not $process.WaitForExit(1000)) {
        if($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {Stop-Process -Id $process.Id -Force;throw 'Own preview timed out.'}
    }
    $process.Refresh()
    if($Mode -eq 'menu') {
        $lines=@((Get-Content (Join-Path $output 'checks.txt'))+(Get-Content (Join-Path $output 'integration.txt')))
        $result=[ordered]@{passed=@($lines | Where-Object {$_ -match '^PASS '}).Count;failed=@($lines | Where-Object {$_ -match '^FAIL '}).Count}
    } else {$result=Get-Content (Join-Path $output 'result.json') -Raw | ConvertFrom-Json}
    Add-Type -AssemblyName System.Drawing
    foreach($bmp in Get-ChildItem $output -Filter *.bmp -File) {
        $image=[Drawing.Image]::FromFile($bmp.FullName)
        try {$image.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png)} finally {$image.Dispose()}
    }
    [ordered]@{created_utc=[DateTime]::UtcNow.ToString('o');runtime=$runtime;executable_sha256=(Get-FileHash $exe).Hash;exit_code=$process.ExitCode;result=$result} |
        ConvertTo-Json -Depth 8 | Set-Content (Join-Path $output 'manifest.json') -Encoding utf8
    $result | ConvertTo-Json -Compress
    if($process.ExitCode -ne 0 -or $result.failed -ne 0) {
        Get-Content (Join-Path $output 'checks.txt') | Select-String '^FAIL';throw 'Integration preview failed.'
    }
} finally {
    [IO.File]::WriteAllBytes($cfg,$cfgBytes)
    if($null -ne $automapBytes){[IO.File]::WriteAllBytes($automap,$automapBytes)}
    elseif(Test-Path -LiteralPath $automap){Remove-Item -LiteralPath $automap}
    foreach($n in $names) {[Environment]::SetEnvironmentVariable($n,$old[$n],'Process')}
}
