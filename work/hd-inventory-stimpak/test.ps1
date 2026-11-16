[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$OutputDirectory = '',
    [string]$Executable = '',
    [string]$AssetPath = '',
    [ValidateSet(0,1)][int]$ExpectedLoaded = 1,
    [ValidateSet(4,8,21,29,30,40)][int]$ItemPid = 40,
    [int]$TimeoutSeconds = 150
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
if ([string]::IsNullOrWhiteSpace($Executable)) { $Executable = Join-Path $runtime 'fallout-ce.exe' }
$exe = (Resolve-Path -LiteralPath $Executable).Path
$testedAsset = if ([string]::IsNullOrWhiteSpace($AssetPath)) {
    if ($ItemPid -eq 40) { Join-Path $runtime 'data/art/hd/inventory/stimpak/stimpak.rgba' } elseif ($ItemPid -eq 29) { Join-Path $runtime 'data/art/hd/inventory/10mm-jhp/ammo.rgba' } elseif ($ItemPid -eq 30) { Join-Path $runtime 'data/art/hd/inventory/10mm-ap/ammo.rgba' } elseif ($ItemPid -eq 21) { Join-Path $runtime 'data/art/hd/inventory/brass-knuckles/knuckles.rgba' } elseif ($ItemPid -eq 8) { Join-Path $runtime 'data/art/hd/inventory/10mm-pistol/pistol.rgba' } else { Join-Path $runtime 'data/art/hd/inventory/knife/knife.rgba' }
} else { [IO.Path]::GetFullPath($AssetPath) }
$testedAssetHash = if (Test-Path -LiteralPath $testedAsset -PathType Leaf) {
    (Get-FileHash -LiteralPath $testedAsset -Algorithm SHA256).Hash
} else { $null }
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) {
    throw 'A Fallout process is running; the preview requires the game mutex. No process was stopped.'
}
foreach ($relative in @('data/maps/V13ENT.SAV','data/maps/V13ENT.MAP','maps/V13ENT.SAV','maps/V13ENT.MAP')) {
    if (Test-Path -LiteralPath (Join-Path $runtime $relative)) {
        throw "Local map override $relative would invalidate original cave setup; it was preserved."
    }
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectPath ('build/hd-inventory-stimpak/preview/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null
$previous = @{}
foreach ($name in @('FALLOUT_HD_HUD_ITEM_PID','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_HUD_ASSET','FALLOUT_HD_HUD_EXPECT_LOADED','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_MENU_PREVIEW')) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
}
$started = Get-Date
try {
    $env:FALLOUT_HD_HUD_ITEM_PID = [string]$ItemPid
    $env:FALLOUT_HD_HUD_PREVIEW = $output
    $env:FALLOUT_HD_HUD_EXPECT_LOADED = [string]$ExpectedLoaded
    $env:FALLOUT_HD_HUD_ASSET = if ([string]::IsNullOrWhiteSpace($AssetPath)) { $null } else { [IO.Path]::GetFullPath($AssetPath) }
    $env:FALLOUT_HD_WORLD_PREVIEW = $null
    $env:FALLOUT_HD_PLAYER_PREVIEW = $null
    $env:FALLOUT_HD_MENU_PREVIEW = $null
    $process = Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not $process.WaitForExit(1000)) {
        if ($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
            Stop-Process -Id $process.Id -Force
            throw 'Own HUD preview process timed out.'
        }
    }
    $process.Refresh()
    $assetHashAfter = if (Test-Path -LiteralPath $testedAsset -PathType Leaf) {
        (Get-FileHash -LiteralPath $testedAsset -Algorithm SHA256).Hash
    } else { $null }
    if ($assetHashAfter -ne $testedAssetHash) { throw 'HUD asset changed during the test; run it again with a stable asset.' }
    $resultPath = Join-Path $output 'result.json'
    if (-not (Test-Path -LiteralPath $resultPath) -or (Get-Item -LiteralPath $resultPath).LastWriteTime -lt $started) {
        throw "HUD preview produced no fresh result; exit $($process.ExitCode)."
    }
    Add-Type -AssemblyName System.Drawing
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $image = [Drawing.Image]::FromFile($bmp.FullName)
        try { $image.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png) }
        finally { $image.Dispose() }
    }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    $manifest = [ordered]@{
        created_utc = (Get-Date).ToUniversalTime().ToString('o')
        executable = $exe
        executable_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        runtime = $runtime
        item_pid = $ItemPid
        expected_loaded = $ExpectedLoaded
        asset_override = $AssetPath
        asset_path = $testedAsset
        asset_sha256 = $testedAssetHash
        exit_code = $process.ExitCode
        result = $result
        captures = @(Get-ChildItem -LiteralPath $output -Filter '*.png' -File | ForEach-Object {
            [ordered]@{ file=$_.Name; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
        })
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $output 'checks.txt')
    if ($process.ExitCode -ne 0 -or $result.failed -ne 0) { throw "HUD preview failed: $($result.failed) checks, exit $($process.ExitCode)." }
    Write-Output "HUD preview: $output"
} finally {
    foreach ($entry in $previous.GetEnumerator()) { [Environment]::SetEnvironmentVariable($entry.Key,$entry.Value,'Process') }
}
