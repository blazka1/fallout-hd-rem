[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent),
    [string]$RuntimeDirectory = 'runtime/hd-world-pilot',
    [string]$OutputDirectory = '',
    [ValidateRange(0, 54)][int]$ExpectedFrameCount = 54,
    [ValidateRange(30, 900)][int]$TimeoutSeconds = 300
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = if ([IO.Path]::IsPathRooted($RuntimeDirectory)) { [IO.Path]::GetFullPath($RuntimeDirectory) } else { Join-Path $projectPath $RuntimeDirectory }
$exe = Join-Path $runtime 'fallout-ce.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Build and install the player-enabled isolated runtime first.' }
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) {
    throw 'A Fallout process is already running. The preview uses the game mutex; close that game before testing.'
}
foreach ($relative in @('data/maps/V13ENT.SAV', 'data/maps/V13ENT.MAP', 'maps/V13ENT.SAV', 'maps/V13ENT.MAP')) {
    if (Test-Path -LiteralPath (Join-Path $runtime $relative)) {
        throw "The test runtime contains $relative. Existing map/save data was preserved; use an isolated original-map runtime."
    }
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectPath ('build/hd-player-male/preview/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$output = if ([IO.Path]::IsPathRooted($OutputDirectory)) { [IO.Path]::GetFullPath($OutputDirectory) } else { [IO.Path]::GetFullPath((Join-Path $projectPath $OutputDirectory)) }
if (Test-Path -LiteralPath (Join-Path $output 'result.json')) { throw 'Output already contains a result; choose a new directory.' }
New-Item -ItemType Directory -Path $output -Force | Out-Null
$savedEnvironment = @{}
$configPath = Join-Path $runtime 'fallout.cfg'
$configBytes = [IO.File]::ReadAllBytes($configPath)
foreach ($name in @('FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_PLAYER_EXPECT_COUNT','FALLOUT_HD_PLAYER_DEMO','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_WORLD_BENCHMARK')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$started = Get-Date
try {
    $env:FALLOUT_HD_WORLD_PREVIEW = $null
    $env:FALLOUT_HD_PLAYER_DEMO = $null
    $env:FALLOUT_HD_PLAYER_PREVIEW = $output
    $env:FALLOUT_HD_PLAYER_EXPECT_COUNT = [string]$ExpectedFrameCount
    $env:FALLOUT_HD_MENU_PREVIEW = $null
    $env:FALLOUT_HD_WORLD_BENCHMARK = $null
    $process = Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not $process.WaitForExit(1000)) {
        if ($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
            Stop-Process -Id $process.Id -Force
            throw "Own player preview process exceeded $TimeoutSeconds seconds. Output: $output"
        }
    }
    $process.Refresh()
    $checks = Join-Path $output 'checks.txt'
    if (Test-Path -LiteralPath $checks) { Get-Content -LiteralPath $checks }
    Add-Type -AssemblyName System.Drawing
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $image = [Drawing.Image]::FromFile($bmp.FullName)
        try { $image.Save([IO.Path]::ChangeExtension($bmp.FullName, '.png'), [Drawing.Imaging.ImageFormat]::Png) }
        finally { $image.Dispose() }
    }
    $resultPath = Join-Path $output 'result.json'
    if (-not (Test-Path -LiteralPath $resultPath)) { throw "Player preview produced no result; exit $($process.ExitCode). Output: $output" }
    if ((Get-Item -LiteralPath $resultPath).LastWriteTime -lt $started) { throw 'Player preview result is stale.' }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    $manifest = [ordered]@{
        created_utc = [DateTime]::UtcNow.ToString('o')
        runtime = $runtime
        executable_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        expected_player_frames = $ExpectedFrameCount
        exit_code = $process.ExitCode
        result = $result
        captures = @(Get-ChildItem -LiteralPath $output -Filter '*.png' -File | ForEach-Object {
            [ordered]@{ file = $_.Name; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
        })
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    Write-Output "Player preview output: $output"
    if ($process.ExitCode -ne 0 -or $result.failed -ne 0) { throw "Player preview failed: exit $($process.ExitCode), $($result.failed) failures." }
} finally {
    [IO.File]::WriteAllBytes($configPath, $configBytes)
    foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
}
