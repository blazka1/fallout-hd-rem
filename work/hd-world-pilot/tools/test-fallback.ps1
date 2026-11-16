[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent),
    [ValidateRange(10, 600)][int]$TimeoutSeconds = 150,
    [switch]$IncludeEmptyRegistry
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$assetDirectory = Join-Path $runtime 'data/art/hd/world-pilot'
$registryPath = Join-Path $assetDirectory 'registry.tsv'
$previewScript = Join-Path $PSScriptRoot 'test.ps1'

function Assert-NoFalloutProcess {
    $running = @(Get-Process -Name 'fallout-ce', 'fallout', 'falloutw', 'fallout1-ce' -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) {
        throw 'A Fallout process is running. Close the game before the isolated fallback test; no process was stopped.'
    }
}

Assert-NoFalloutProcess
foreach ($required in @($previewScript, (Join-Path $runtime 'fallout-ce.exe'),
    (Join-Path $assetDirectory 'cav1000.rgba'), (Join-Path $assetDirectory 'rock03.rgba'), $registryPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing prepared runtime file: $required" }
}

# The narrow asset-fallback cases intentionally expose only IDs 1 and 2 to the
# loader. All other packaged files remain on disk and are never modified.
$registryLines = [IO.File]::ReadAllLines($registryPath)
$fixtureRows = @($registryLines | Where-Object { $_ -match '^\s*(1|2)\s+' })
$fixtureIds = @($fixtureRows | ForEach-Object { [int](($_.Trim() -split '\s+')[0]) } | Sort-Object -Unique)
if ($fixtureIds.Count -ne 2 -or $fixtureIds[0] -ne 1 -or $fixtureIds[1] -ne 2) {
    throw 'The prepared full registry must contain stable asset IDs 1 and 2. Runtime files were not changed.'
}
$registryDataRows = @($registryLines | Where-Object { $_ -match '^\s*\d+\s+' })
$fixtureRegistry = "# Fallback test fixture: only stable asset IDs 1 and 2`n" + ($fixtureRows -join "`n") + "`n"

# Every invocation owns its output and backup directory. Existing reports are never reused.
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDirectory = Join-Path $projectPath ('build/hd-world-pilot/fallback/' + $runId)
$backupDirectory = Join-Path $runDirectory 'backup'
New-Item -ItemType Directory -Path $backupDirectory | Out-Null
$originals = @()
foreach ($name in @('cav1000', 'rock03')) {
    $path = Join-Path $assetDirectory ($name + '.rgba')
    $backup = Join-Path $backupDirectory ($name + '.rgba')
    $bytes = [IO.File]::ReadAllBytes($path)
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    [IO.File]::WriteAllBytes($backup, $bytes)
    if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $hash) {
        throw "Backup verification failed: $backup. Runtime files were not changed."
    }
    $originals += [pscustomobject]@{ Name = $name; Path = $path; Backup = $backup; Bytes = $bytes; Sha256 = $hash }
}
$registryBytes = [IO.File]::ReadAllBytes($registryPath)
$registryHash = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
$registryBackup = Join-Path $backupDirectory 'registry.tsv'
[IO.File]::WriteAllBytes($registryBackup, $registryBytes)
if ((Get-FileHash -LiteralPath $registryBackup -Algorithm SHA256).Hash -ne $registryHash) {
    throw "Registry backup verification failed: $registryBackup. Runtime files were not changed."
}
$registryOriginal = [pscustomobject]@{ Name = 'registry'; Path = $registryPath; Backup = $registryBackup; Bytes = $registryBytes; Sha256 = $registryHash }
$allOriginals = @($originals) + @($registryOriginal)
@($allOriginals | ForEach-Object {
    [ordered]@{ name = $_.Name; runtime_path = $_.Path; backup_path = $_.Backup; sha256 = $_.Sha256; length = $_.Bytes.Length }
}) | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backupDirectory 'manifest.json') -Encoding utf8

function Restore-OriginalRuntimeFiles {
    $restoreErrors = [System.Collections.Generic.List[string]]::new()
    # Attempt every restore even if one write fails, including the full registry.
    foreach ($original in $allOriginals) {
        try { [IO.File]::WriteAllBytes($original.Path, $original.Bytes) }
        catch { $restoreErrors.Add("Write failed for $($original.Path): $($_.Exception.Message)") }
    }
    foreach ($original in $allOriginals) {
        try {
            if ((Get-FileHash -LiteralPath $original.Path -Algorithm SHA256).Hash -ne $original.Sha256) {
                $restoreErrors.Add("Hash mismatch for $($original.Path); verified backup: $($original.Backup)")
            }
        } catch { $restoreErrors.Add("Verification failed for $($original.Path): $($_.Exception.Message)") }
    }
    if ($restoreErrors.Count -gt 0) { throw ($restoreErrors -join "`n") }
}

$previousEnvironment = @{}
foreach ($key in @('FALLOUT_HD_WORLD_EXPECT_ASSETS', 'FALLOUT_HD_WORLD_PREVIEW', 'FALLOUT_HD_MENU_PREVIEW')) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
$cases = @(
    [pscustomobject]@{ Name = 'both-assets-missing'; Mask = 0; Broken = 'both' },
    [pscustomobject]@{ Name = 'malformed-floor-header'; Mask = 2; Broken = 'cav1000' },
    [pscustomobject]@{ Name = 'malformed-rock-header'; Mask = 1; Broken = 'rock03' }
)
if ($IncludeEmptyRegistry) {
    $cases += [pscustomobject]@{ Name = 'empty-registry'; Mask = 0; Broken = 'registry-empty' }
}
$caseReports = [System.Collections.Generic.List[object]]::new()
$failure = $null
$restored = $false
try {
    foreach ($case in $cases) {
        Assert-NoFalloutProcess
        Restore-OriginalRuntimeFiles
        [IO.File]::WriteAllText($registryPath, $fixtureRegistry, [Text.Encoding]::ASCII)
        $caseDirectory = Join-Path $runDirectory $case.Name
        New-Item -ItemType Directory -Path $caseDirectory | Out-Null
        if ($case.Broken -eq 'both') {
            # Only these two verified runtime files are removed, never a directory.
            foreach ($original in $originals) { Remove-Item -LiteralPath $original.Path }
        } elseif ($case.Broken -eq 'registry-empty') {
            [IO.File]::WriteAllText($registryPath, "# Empty registry test fixture; all RGBA files remain intact.`n", [Text.Encoding]::ASCII)
        } else {
            $original = $originals | Where-Object { $_.Name -eq $case.Broken }
            [byte[]]$malformed = $original.Bytes.Clone()
            [Array]::Copy([Text.Encoding]::ASCII.GetBytes('BAD!'), 0, $malformed, 0, 4)
            [IO.File]::WriteAllBytes($original.Path, $malformed)
        }

        $env:FALLOUT_HD_WORLD_EXPECT_ASSETS = [string]$case.Mask
        & $previewScript -ProjectRoot $projectPath -OutputDirectory $caseDirectory -TimeoutSeconds $TimeoutSeconds |
            Tee-Object -FilePath (Join-Path $caseDirectory 'test-output.txt')
        $result = Get-Content -LiteralPath (Join-Path $caseDirectory 'result.json') -Raw | ConvertFrom-Json
        $caseReports.Add([ordered]@{
            name = $case.Name
            expected_asset_mask = $case.Mask
            registry_fixture = if ($case.Broken -eq 'registry-empty') { 'empty_registry' } else { 'only_stable_asset_ids_1_and_2' }
            registry_sha256_during_case = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash
            output = $caseDirectory
            result = $result
        })
        Restore-OriginalRuntimeFiles
    }
} catch {
    $failure = $_.Exception.Message
    throw
} finally {
    try {
        Restore-OriginalRuntimeFiles
        $restored = $true
    } finally {
        foreach ($key in $previousEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], 'Process')
        }
        [ordered]@{
            created = (Get-Date).ToUniversalTime().ToString('o')
            runtime = $runtime
            backup_directory = $backupDirectory
            registry_fixture_description = 'Asset fallback cases use only original registry rows for stable IDs 1 and 2; other asset files stay on disk unchanged. The full registry is restored afterward.'
            original_registry_sha256 = $registryHash
            original_registry_data_rows = $registryDataRows.Count
            narrow_fixture_asset_ids = @(1, 2)
            empty_registry_case_requested = [bool]$IncludeEmptyRegistry
            expected_cases = $cases.Count
            completed_cases = $caseReports.Count
            cases = @($caseReports.ToArray())
            assets_restored_and_hash_verified = $restored
            full_registry_restored_and_hash_verified = $restored
            failure = $failure
        } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runDirectory 'manifest.json') -Encoding utf8
        Write-Output "Fallback output: $runDirectory"
        Write-Output "Runtime assets and full registry restored and hash-verified: $restored"
    }
}
