[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent),
    [ValidateRange(10, 600)][int]$TimeoutSeconds = 150
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$assetDirectory = Join-Path $runtime 'data/art/hd/world-pilot'
$registryPath = Join-Path $assetDirectory 'registry.tsv'
$executable = Join-Path $runtime 'fallout-ce.exe'
$previewScript = Join-Path $PSScriptRoot 'test.ps1'

function Assert-NoFalloutProcess {
    if (@(Get-Process -Name 'fallout-ce', 'fallout', 'falloutw', 'fallout1-ce' -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'A Fallout process is running. Close the game before this test; no process was stopped.'
    }
}

Assert-NoFalloutProcess
foreach ($path in @($previewScript, $executable, $registryPath,
    (Join-Path $assetDirectory 'cav1000.rgba'), (Join-Path $assetDirectory 'rock03.rgba'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing prepared runtime file: $path" }
}
$registryBytes = [IO.File]::ReadAllBytes($registryPath)
$registryHash = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
$executableHash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
$lines = [IO.File]::ReadAllLines($registryPath)
$floorRows = @($lines | Where-Object { $_ -match '^\s*1\s+' } | ForEach-Object {
    $fields = $_.Trim() -split '\s+'
    if ($fields.Count -lt 5) { throw 'Invalid stable floor registry row.' }
    ($fields[0..4] -join "`t")
})
$rockRows = @($lines | Where-Object { $_ -match '^\s*2\s+' } | ForEach-Object {
    $fields = $_.Trim() -split '\s+'
    if ($fields.Count -lt 5 -or [int]$fields[1] -ne 33554605) { throw 'Expected the original rock03 FID for stable ID2.' }
    ($fields[0..4] -join "`t")
})
if ($floorRows.Count -eq 0 -or $rockRows.Count -eq 0) { throw 'Stable floorID1 and rockID2 rows are required.' }

# New immutable evidence directory; no existing report or asset is repurposed.
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDirectory = Join-Path $projectPath ('build/hd-world-pilot/frame-fallback/' + $runId)
$backupDirectory = Join-Path $runDirectory 'backup'
New-Item -ItemType Directory -Path $backupDirectory | Out-Null
$backupPath = Join-Path $backupDirectory 'registry.tsv'
[IO.File]::WriteAllBytes($backupPath, $registryBytes)
if ((Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash -ne $registryHash) {
    throw 'Registry backup verification failed; runtime was not changed.'
}
$assetHashes = @('cav1000.rgba', 'rock03.rgba') | ForEach-Object {
    [ordered]@{ file = $_; sha256 = (Get-FileHash -LiteralPath (Join-Path $assetDirectory $_) -Algorithm SHA256).Hash }
}
[ordered]@{ registry_path = $registryPath; registry_sha256 = $registryHash; executable_sha256 = $executableHash; assets = $assetHashes } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupDirectory 'manifest.json') -Encoding utf8

function Restore-Registry {
    [IO.File]::WriteAllBytes($registryPath, $registryBytes)
    if ((Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash -ne $registryHash) {
        throw "Registry restore failed; verified backup: $backupPath"
    }
}

$previousEnvironment = @{}
foreach ($key in @('FALLOUT_HD_WORLD_EXPECT_ASSETS', 'FALLOUT_HD_WORLD_EXPECT_COUNT',
    'FALLOUT_HD_WORLD_PREVIEW', 'FALLOUT_HD_MENU_PREVIEW')) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
$cases = @(
    [pscustomobject]@{ Name = 'floor-only-classic-rock'; Mask = 1; Frame = $null },
    [pscustomobject]@{ Name = 'rock-frame7-only'; Mask = 3; Frame = 7 },
    [pscustomobject]@{ Name = 'rock-frame0-positive-control'; Mask = 3; Frame = 0 }
)
$caseReports = [System.Collections.Generic.List[object]]::new()
$comparisons = [ordered]@{}
$comparisonPassed = 0
$comparisonFailed = 0
$failure = $null
$restored = $false
try {
    foreach ($case in $cases) {
        Assert-NoFalloutProcess
        Restore-Registry
        $fixture = @('# Exact-frame lookup fixture; original art and object frames stay unchanged.') + $floorRows
        if ($null -ne $case.Frame) { $fixture += @($rockRows | ForEach-Object { $_ + "`t" + [string]$case.Frame }) }
        [IO.File]::WriteAllText($registryPath, ($fixture -join "`n") + "`n", [Text.Encoding]::ASCII)
        $caseDirectory = Join-Path $runDirectory $case.Name
        New-Item -ItemType Directory -Path $caseDirectory | Out-Null
        $env:FALLOUT_HD_WORLD_EXPECT_ASSETS = [string]$case.Mask
        & $previewScript -ProjectRoot $projectPath -OutputDirectory $caseDirectory -TimeoutSeconds $TimeoutSeconds |
            Tee-Object -FilePath (Join-Path $caseDirectory 'test-output.txt')
        $result = Get-Content -LiteralPath (Join-Path $caseDirectory 'result.json') -Raw | ConvertFrom-Json
        $manifest = Get-Content -LiteralPath (Join-Path $caseDirectory 'manifest.json') -Raw | ConvertFrom-Json
        if ($result.failed -ne 0 -or $manifest.executable_sha256 -ne $executableHash) { throw 'Case failed or executable changed.' }
        $caseReports.Add([ordered]@{
            name = $case.Name
            expected_asset_mask = $case.Mask
            registered_rock_frame = $case.Frame
            actual_original_rock_frame = 0
            registry_sha256 = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
            output = $caseDirectory
            classic_capture_sha256 = (Get-FileHash -LiteralPath (Join-Path $caseDirectory 'fallback-classic.bmp') -Algorithm SHA256).Hash
            hd_capture_sha256 = (Get-FileHash -LiteralPath (Join-Path $caseDirectory 'fallback-hd.bmp') -Algorithm SHA256).Hash
            result = $result
        })
        Restore-Registry
    }
    # Identical classic captures establish deterministic real scenes across runs.
    # Then frame7-only must draw exactly the same classic rock as the no-rock-HD
    # control, while an explicitly registered frame0 must visibly replace it.
    $comparisons['classic_controls_pixel_identical'] = (
        $caseReports[0].classic_capture_sha256 -eq $caseReports[1].classic_capture_sha256 -and
        $caseReports[0].classic_capture_sha256 -eq $caseReports[2].classic_capture_sha256)
    $comparisons['missing_frame0_matches_classic_rock_control'] = (
        $caseReports[0].hd_capture_sha256 -eq $caseReports[1].hd_capture_sha256)
    $comparisons['explicit_frame0_changes_rock_pixels'] = (
        $caseReports[0].hd_capture_sha256 -ne $caseReports[2].hd_capture_sha256)
    foreach ($entry in $comparisons.GetEnumerator()) {
        if ($entry.Value) { $comparisonPassed++ } else { $comparisonFailed++ }
        $prefix = if ($entry.Value) { 'PASS ' } else { 'FAIL ' }
        Write-Output ($prefix + $entry.Key)
    }
    if ($comparisonFailed -ne 0) { throw 'Exact-frame image comparison failed; see the separate run evidence.' }
} catch {
    $failure = $_.Exception.Message
    throw
} finally {
    try {
        Restore-Registry
        foreach ($asset in $assetHashes) {
            if ((Get-FileHash -LiteralPath (Join-Path $assetDirectory $asset.file) -Algorithm SHA256).Hash -ne $asset.sha256) {
                throw "Unexpected asset mutation: $($asset.file). This script only edits the registry."
            }
        }
        $restored = $true
    } finally {
        foreach ($key in $previousEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], 'Process')
        }
        $casePassed = ($caseReports | ForEach-Object { $_.result.passed } | Measure-Object -Sum).Sum
        [ordered]@{
            created = (Get-Date).ToUniversalTime().ToString('o')
            scope = 'Exact-frame loader fallback using real original rock03 frame0; not a timed animated-door script test.'
            runtime = $runtime
            executable_sha256 = $executableHash
            original_registry_sha256 = $registryHash
            registry_backup = $backupPath
            completed_cases = $caseReports.Count
            cases = @($caseReports.ToArray())
            comparison_checks = [ordered]@{ passed = $comparisonPassed; failed = $comparisonFailed; checks = $comparisons }
            passed = [int]$casePassed + $comparisonPassed
            failed = $comparisonFailed + $(if ($failure -and $comparisonFailed -eq 0) { 1 } else { 0 })
            registry_restored_and_hash_verified = $restored
            failure = $failure
        } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runDirectory 'manifest.json') -Encoding utf8
        Write-Output "Exact-frame fallback output: $runDirectory"
        Write-Output "Original full registry restored and assets hash-verified: $restored"
    }
}
