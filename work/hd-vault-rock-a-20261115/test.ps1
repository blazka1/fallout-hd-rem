param(
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$OutputDirectory = '',
    [int]$TimeoutSeconds = 150,
    [int]$ExpectedAssetCount = 0
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$exe = Join-Path $runtime 'fallout-vault-rock-test.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw 'Build and prepare the isolated HD world runtime first.'
}
if (Get-Process -Name 'fallout-ce','fallout-cave-test','fallout-wall-test','fallout-vault-rock-test' -ErrorAction SilentlyContinue) {
    throw 'A Fallout process is already running. The preview uses the game mutex; close the game before testing.'
}
# The loader prefers SAV files. Do not remove saves: fail instead of testing a changed map.
foreach ($relative in @('data/maps/V13ENT.SAV', 'data/maps/V13ENT.MAP', 'maps/V13ENT.SAV', 'maps/V13ENT.MAP')) {
    if (Test-Path -LiteralPath (Join-Path $runtime $relative)) {
        throw "The isolated runtime contains $relative; original-map preview requires an untouched map. Existing files were preserved."
    }
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectPath ('build/hd-world-pilot/preview/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output -Force | Out-Null
$previousWorld = $env:FALLOUT_HD_WORLD_PREVIEW
$previousMenu = $env:FALLOUT_HD_MENU_PREVIEW
$previousCount = $env:FALLOUT_HD_WORLD_EXPECT_COUNT
if ($ExpectedAssetCount -eq 0) {
    $ExpectedAssetCount = (Get-Content -LiteralPath (Join-Path $runtime 'data/art/hd/world-pilot/manifest.json') -Raw | ConvertFrom-Json).asset_count
}
if ($ExpectedAssetCount -lt 159 -or $ExpectedAssetCount -gt 255) { throw 'Invalid expected HD resource count.' }
$started = Get-Date
$automapPath = Join-Path $runtime 'data/MAPS/AUTOMAP.DB'
$automapBefore = if (Test-Path -LiteralPath $automapPath) { [System.IO.File]::ReadAllBytes($automapPath) } else { $null }
try {
    $env:FALLOUT_HD_WORLD_PREVIEW = $output
    $env:FALLOUT_HD_MENU_PREVIEW = $null
    $env:FALLOUT_HD_WORLD_EXPECT_COUNT = [string]$ExpectedAssetCount
    $process = Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $process.WaitForExit(1000)) {
        if ($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
            Stop-Process -Id $process.Id -Force
            throw "Own HD world preview process exceeded $TimeoutSeconds seconds. Output: $output"
        }
    }
    $process.Refresh()
    $checksPath = Join-Path $output 'checks.txt'
    if (Test-Path -LiteralPath $checksPath) { Get-Content -LiteralPath $checksPath }
    # Convert captured renderer pixels losslessly for review; no asset processing.
    Add-Type -AssemblyName System.Drawing
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $image = [System.Drawing.Image]::FromFile($bmp.FullName)
        try {
            $image.Save([System.IO.Path]::ChangeExtension($bmp.FullName, '.png'), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $image.Dispose() }
    }
    $resultPath = Join-Path $output 'result.json'
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
        throw "Preview produced no result.json; process exit $($process.ExitCode). Output: $output"
    }
    if ((Get-Item -LiteralPath $resultPath).LastWriteTime -lt $started) {
        throw 'Preview result is stale.'
    }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    $manifest = [ordered]@{
        created = (Get-Date).ToUniversalTime().ToString('o')
        runtime = $runtime
        executable_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        exit_code = $process.ExitCode
        result = $result
        captures = @(Get-ChildItem -LiteralPath $output -Filter '*.png' -File | ForEach-Object {
            [ordered]@{ file = $_.Name; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
        })
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    Write-Output "Preview output: $output"
    if ($process.ExitCode -ne 0 -or $result.failed -ne 0) {
        throw "HD world preview failed: exit $($process.ExitCode), $($result.failed) failed checks."
    }
} finally {
    if ($null -ne $automapBefore) { [System.IO.File]::WriteAllBytes($automapPath, $automapBefore) }
    $env:FALLOUT_HD_WORLD_PREVIEW = $previousWorld
    $env:FALLOUT_HD_MENU_PREVIEW = $previousMenu
    $env:FALLOUT_HD_WORLD_EXPECT_COUNT = $previousCount
}

