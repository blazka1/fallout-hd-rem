[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TestManifest,
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path.TrimEnd('\','/')
$runtime = [IO.Path]::GetFullPath((Join-Path $project 'runtime/hd-world-pilot'))
$sourceExe = Join-Path $project 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
$sourceAsset = Join-Path $project 'assets/hd/inventory/brass-knuckles/v1/knuckles.rgba'
$targetExe = Join-Path $runtime 'fallout-ce.exe'
$targetAsset = Join-Path $runtime 'data/art/hd/inventory/brass-knuckles/knuckles.rgba'

function Assert-Within {
    param([string]$Path,[string]$Parent)
    $absolute = [IO.Path]::GetFullPath($Path)
    $boundary = [IO.Path]::GetFullPath($Parent).TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    if (-not $absolute.StartsWith($boundary,[StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing a path outside $Parent : $absolute"
    }
    return $absolute
}

function Assert-RuntimeStopped {
    # Include renamed preview executables and any other process in this runtime.
    $boundary = $runtime.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    $running = @(Get-Process | ForEach-Object {
        $processPath = $null
        try { $processPath = $_.Path } catch { }
        if ($processPath -and $processPath.StartsWith($boundary,[StringComparison]::OrdinalIgnoreCase)) {
            [pscustomobject]@{ id=$_.Id; path=$processPath }
        }
    })
    if ($running.Count -gt 0) {
        throw ('Runtime processes are running; no process was stopped: ' + (($running | ForEach-Object { "$($_.id) $($_.path)" }) -join ', '))
    }
}

function Write-Json {
    param([string]$Path,$Value)
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding utf8
}

$targetExe = Assert-Within $targetExe $runtime
$targetAsset = Assert-Within $targetAsset $runtime
[void](Assert-Within $runtime $project)
foreach ($path in @($sourceExe,$sourceAsset,(Join-Path $runtime 'fallout.cfg'),$targetExe)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required file missing: $path" }
}
$manifestPath = (Resolve-Path -LiteralPath $TestManifest).Path
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$requiredFields = @('created_utc','executable_sha256','asset_path','asset_sha256','exit_code','expected_loaded','result')
foreach ($field in $requiredFields) {
    if ($manifest.PSObject.Properties.Name -notcontains $field) { throw "HUD test manifest lacks $field" }
}
if ($manifest.result.PSObject.Properties.Name -notcontains 'failed' -or
    $manifest.result.PSObject.Properties.Name -notcontains 'passed' -or
    [int]$manifest.exit_code -ne 0 -or [int]$manifest.result.failed -ne 0 -or
    [int]$manifest.result.passed -le 0 -or [int]$manifest.expected_loaded -ne 1) {
    throw 'Require a successful HUD test with the HD asset loaded, not a fallback test.'
}
if ($manifest.PSObject.Properties.Name -notcontains 'item_pid' -or [int]$manifest.item_pid -ne 21) { throw 'Require the actual PID21 knuckles loaded test.' }
$exeHash = (Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash
if ($exeHash -ne [string]$manifest.executable_sha256) { throw 'Tested EXE hash does not match the build EXE.' }
# PowerShell 7.5 may deserialize ISO dates directly as DateTime. Casting that
# object to string drops its UTC kind and would reinterpret it in local time.
$testTime = if ($manifest.created_utc -is [DateTime]) {
    $manifest.created_utc.ToUniversalTime()
} elseif ($manifest.created_utc -is [DateTimeOffset]) {
    $manifest.created_utc.UtcDateTime
} else {
    [DateTimeOffset]::Parse([string]$manifest.created_utc).UtcDateTime
}
if ($testTime -lt (Get-Item -LiteralPath $sourceExe).LastWriteTimeUtc -or
    (Get-Item -LiteralPath $manifestPath).LastWriteTimeUtc -lt (Get-Item -LiteralPath $sourceExe).LastWriteTimeUtc) {
    throw 'HUD test manifest predates this build; run the HUD test again.'
}
if ($testTime -gt [DateTime]::UtcNow.AddMinutes(5)) { throw 'HUD test manifest has an invalid future timestamp.' }

# The installed F1HD file is already losslessly packed. Validate, never edit pixels.
$asset = [IO.File]::ReadAllBytes($sourceAsset)
$expectedLength = 20 + 324 * 260 * 4
if ($asset.Length -ne $expectedLength -or [Text.Encoding]::ASCII.GetString($asset,0,4) -ne 'F1HD' -or
    [BitConverter]::ToUInt32($asset,4) -ne 1 -or [BitConverter]::ToUInt32($asset,8) -ne 324 -or
    [BitConverter]::ToUInt32($asset,12) -ne 260 -or [BitConverter]::ToUInt32($asset,16) -ne 4) {
    throw "Invalid knuckles F1HD file: require version1,324x260,RGBA8 and exactly $expectedLength bytes."
}
$assetHash = (Get-FileHash -LiteralPath $sourceAsset -Algorithm SHA256).Hash
if ($assetHash -ne [string]$manifest.asset_sha256) { throw 'Tested HUD asset hash does not match the selected knuckles RGBA. Run the test with this asset.' }
Assert-RuntimeStopped
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backup = Assert-Within (Join-Path $project ('build/backups/before-hd-knuckles-install-' + $stamp)) $project
if (Test-Path -LiteralPath $backup) { throw "Backup directory already exists: $backup" }
New-Item -ItemType Directory -Path $backup | Out-Null
$files = @(
    [pscustomobject]@{ source=$sourceExe; target=$targetExe; sha256=$exeHash; backup=(Join-Path $backup 'fallout-ce.exe'); existed=$true; old_sha256=$null },
    [pscustomobject]@{ source=$sourceAsset; target=$targetAsset; sha256=$assetHash; backup=(Join-Path $backup 'knuckles.rgba'); existed=(Test-Path -LiteralPath $targetAsset -PathType Leaf); old_sha256=$null }
)
foreach ($file in $files) {
    if ($file.existed) {
        $file.old_sha256 = (Get-FileHash -LiteralPath $file.target -Algorithm SHA256).Hash
        Copy-Item -LiteralPath $file.target -Destination $file.backup
        if ((Get-FileHash -LiteralPath $file.backup -Algorithm SHA256).Hash -ne $file.old_sha256) { throw 'Backup verification failed.' }
    }
}
Write-Json (Join-Path $backup 'backup.json') ([ordered]@{
    created_utc=[DateTime]::UtcNow.ToString('o'); test_manifest=$manifestPath;
    test_manifest_sha256=(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash;
    files=$files
})
Assert-RuntimeStopped
$changed = [Collections.Generic.List[object]]::new()
try {
    foreach ($file in $files) {
        if ((Get-FileHash -LiteralPath $file.source -Algorithm SHA256).Hash -ne $file.sha256) { throw 'Source changed after validation.' }
        New-Item -ItemType Directory -Force -Path (Split-Path $file.target -Parent) | Out-Null
        $changed.Add($file)
        Copy-Item -LiteralPath $file.source -Destination $file.target -Force
        if ((Get-FileHash -LiteralPath $file.target -Algorithm SHA256).Hash -ne $file.sha256) { throw "Installed hash mismatch: $($file.target)" }
    }
} catch {
    $failure = $_
    # Revert only files in this transaction; every destination was confined above.
    foreach ($file in $changed) {
        [void](Assert-Within $file.target $runtime)
        if ($file.existed) { Copy-Item -LiteralPath $file.backup -Destination $file.target -Force }
        elseif (Test-Path -LiteralPath $file.target -PathType Leaf) { Remove-Item -LiteralPath $file.target -Force }
    }
    Write-Json (Join-Path $backup 'failed-install.json') ([ordered]@{ status='rolled_back'; error=[string]$failure; files=$files })
    throw $failure
}
$receiptDirectory = Assert-Within (Join-Path $project 'build/hd-inventory-brass-knuckles/installations') $project
New-Item -ItemType Directory -Force -Path $receiptDirectory | Out-Null
$receiptPath = Join-Path $receiptDirectory ($stamp + '.json')
Write-Json $receiptPath ([ordered]@{
    status='installed_and_hash_verified'; installed_utc=[DateTime]::UtcNow.ToString('o');
    runtime=$runtime; backup_directory=$backup; test_manifest=$manifestPath;
    test_manifest_sha256=(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash;
    test_passed=[int]$manifest.result.passed; test_failed=[int]$manifest.result.failed;
    files=$files; rgba_bytes=$expectedLength;
    scope='Only pilot EXE and knuckles.rgba installed. No configuration, other art, saves, DAT or shared integration manifest changed.'
})
Write-Output "Installed HUD EXE and lossless knuckles RGBA. Receipt: $receiptPath"
