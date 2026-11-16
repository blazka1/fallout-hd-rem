param(
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$OutputDirectory = '',
    [string]$Label = 'measurement',
    [int]$TimeoutSeconds = 240,
    [int]$ExpectedAssetCount = 0
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$exe = Join-Path $runtime 'fallout-cave-test.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw 'Build and prepare the isolated HD world runtime first.'
}
if (Get-Process -Name 'fallout-ce','fallout-cave-test' -ErrorAction SilentlyContinue) {
    throw 'A Fallout process is already running. Close the game before benchmarking.'
}
foreach ($relative in @('data/maps/V13ENT.SAV', 'data/maps/V13ENT.MAP', 'maps/V13ENT.SAV', 'maps/V13ENT.MAP')) {
    if (Test-Path -LiteralPath (Join-Path $runtime $relative)) {
        throw "The runtime contains $relative; benchmark requires the original map. Existing files were preserved."
    }
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectPath ('build/hd-world-pilot/benchmark/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
}
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath (Join-Path $output 'benchmark.json')) {
    throw 'Use a fresh output directory; benchmark evidence will not be overwritten.'
}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$environmentNames = @(
    'FALLOUT_HD_WORLD_PREVIEW', 'FALLOUT_HD_WORLD_BENCHMARK',
    'FALLOUT_HD_WORLD_EXPECT_ASSETS', 'FALLOUT_HD_MENU_PREVIEW', 'FALLOUT_HD_WORLD_EXPECT_COUNT'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$started = Get-Date
$exeHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$registry = Join-Path $runtime 'data/art/hd/world-pilot/registry.tsv'
if (-not (Test-Path -LiteralPath $registry)) {
    throw "Runtime registry not found: $registry"
}
$registryHash = (Get-FileHash -LiteralPath $registry -Algorithm SHA256).Hash
$buildManifestPath = Join-Path $projectPath 'build/hd-world-pilot/logs/build-manifest.json'
$sourceHashesPath = Join-Path $projectPath 'build/hd-world-pilot/logs/source-hashes.json'
$compiledBuild = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
if ($compiledBuild.executable_sha256 -ne $exeHash) {
    throw 'Current build evidence does not match the runtime executable; preserve matching build evidence before benchmarking.'
}
$compiledSources = Get-Content -LiteralPath $sourceHashesPath -Raw | ConvertFrom-Json
$compiledHarness = @($compiledSources | Where-Object path -eq 'src/game/hd_world_pilot_test.cc')
if ($compiledHarness.Count -ne 1) { throw 'Build evidence has no unique test module hash.' }
# Freeze compiler-verified source evidence before another agent starts a later build.
Copy-Item -LiteralPath $buildManifestPath -Destination (Join-Path $output 'compiled-build-manifest.json')
Copy-Item -LiteralPath $sourceHashesPath -Destination (Join-Path $output 'compiled-source-hashes.json')
$buildManifestHash = (Get-FileHash -LiteralPath (Join-Path $output 'compiled-build-manifest.json') -Algorithm SHA256).Hash
$sourceHashesHash = (Get-FileHash -LiteralPath (Join-Path $output 'compiled-source-hashes.json') -Algorithm SHA256).Hash
if ($ExpectedAssetCount -eq 0) {
    $ExpectedAssetCount = (Get-Content -LiteralPath (Join-Path $runtime 'data/art/hd/world-pilot/manifest.json') -Raw | ConvertFrom-Json).asset_count
}
if ($ExpectedAssetCount -lt 159 -or $ExpectedAssetCount -gt 255) { throw 'Invalid expected HD resource count.' }
try {
    $env:FALLOUT_HD_WORLD_PREVIEW = $output
    $env:FALLOUT_HD_WORLD_BENCHMARK = $output
    $env:FALLOUT_HD_WORLD_EXPECT_ASSETS = $null
    $env:FALLOUT_HD_MENU_PREVIEW = $null
    $env:FALLOUT_HD_WORLD_EXPECT_COUNT = [string]$ExpectedAssetCount
    $process = Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $process.WaitForExit(1000)) {
        if ($timer.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
            Stop-Process -Id $process.Id -Force
            throw "Own benchmark process exceeded $TimeoutSeconds seconds. Output: $output"
        }
    }
    $process.Refresh()
    $checksPath = Join-Path $output 'checks.txt'
    if (Test-Path -LiteralPath $checksPath) { Get-Content -LiteralPath $checksPath }
    $resultPath = Join-Path $output 'benchmark.json'
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
        throw "No benchmark.json; process exit $($process.ExitCode). Output: $output"
    }
    if ((Get-Item -LiteralPath $resultPath).LastWriteTime -lt $started) {
        throw 'Benchmark result is stale.'
    }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $exeHash) {
        throw 'The executable changed during the benchmark.'
    }
    if ((Get-FileHash -LiteralPath $registry -Algorithm SHA256).Hash -ne $registryHash) {
        throw 'The registry changed during the benchmark.'
    }
    $manifest = [ordered]@{
        created = (Get-Date).ToUniversalTime().ToString('o')
        label = $Label
        runtime = $runtime
        executable_sha256 = $exeHash
        registry_sha256 = $registryHash
        harness_sha256 = $compiledHarness[0].sha256
        harness_hash_source = 'compiled-source-hashes.json: src/game/hd_world_pilot_test.cc; matching compiled-build-manifest.json executable_sha256'
        compiled_build_manifest_sha256 = $buildManifestHash
        compiled_source_hashes_sha256 = $sourceHashesHash
        result_sha256 = (Get-FileHash -LiteralPath $resultPath -Algorithm SHA256).Hash
        exit_code = $process.ExitCode
        elapsed_seconds = $timer.Elapsed.TotalSeconds
        result = $result
    }
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    $result.rows | Select-Object actual_width, actual_height, mode, workload, median_ms, p95_ms | Format-Table -AutoSize | Out-String | Write-Output
    Write-Output "Benchmark output: $output"
    if ($process.ExitCode -ne 0 -or $result.failed -ne 0 -or @($result.rows).Count -ne 16) {
        throw "Benchmark failed: exit $($process.ExitCode), $($result.failed) failed checks."
    }
} finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}
