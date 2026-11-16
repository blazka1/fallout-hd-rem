[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$out = Join-Path $root 'build/combat-crash-fix'
$candidate = Join-Path $out 'verified-candidate.exe'
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$target = Join-Path $runtime 'fallout-ce.exe'
if (Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue) {
    throw 'A Fallout instance is running. No process was stopped and no EXE was replaced.'
}
$hash = (Get-FileHash -LiteralPath $candidate).Hash
$checks = @()
foreach ($name in @('fixed-v1','world-regression','menu-regression')) {
    $manifest = Get-Content -LiteralPath (Join-Path $out "$name/manifest.json") -Raw | ConvertFrom-Json
    if ($manifest.executable_sha256 -ne $hash -or $manifest.exit_code -ne 0 -or $manifest.failed -ne 0 -or $manifest.passed -le 0) {
        throw "Candidate has no successful matching report: $name"
    }
    $checks += [ordered]@{name=$name;passed=$manifest.passed;failed=$manifest.failed}
}
$source = Join-Path $root 'work/hd-world-pilot/fallout1-ce-main'
$sourceHashes = Get-Content -LiteralPath (Join-Path $out 'source-hashes.json') -Raw | ConvertFrom-Json
foreach ($entry in $sourceHashes) {
    if ((Get-FileHash -LiteralPath (Join-Path $source $entry.path)).Hash -ne $entry.sha256) {
        throw "Source changed since the tested build: $($entry.path). Rebuild and retest instead of installing a stale EXE."
    }
}
# Snapshot everything alongside the EXE. Installation writes just the EXE.
$protected = @(Get-ChildItem -LiteralPath $runtime -Recurse -File | Where-Object {$_.FullName -ne $target} | ForEach-Object {
    [ordered]@{path=$_.FullName;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash}
})
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backup = Join-Path $root "build/backups/before-combat-crash-install-$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null
$oldHash = (Get-FileHash -LiteralPath $target).Hash
Copy-Item -LiteralPath $target -Destination (Join-Path $backup 'fallout-ce.exe')
if ((Get-FileHash -LiteralPath (Join-Path $backup 'fallout-ce.exe')).Hash -ne $oldHash) {throw 'Backup hash mismatch'}
$protected | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'protected-runtime-files.json') -Encoding utf8
Copy-Item -LiteralPath $candidate -Destination $target -Force
if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) {throw 'Installed hash mismatch'}
foreach ($entry in $protected) {
    if ((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256) {throw "Protected runtime file changed: $($entry.path)"}
}
[ordered]@{
    component='Fallout 1.0 combat message compatibility';status='installed-and-verified';
    installed_utc=[DateTime]::UtcNow.ToString('o');executable=$target;executable_sha256=$hash;
    previous_sha256=$oldHash;backup=$backup;checks=$checks;
    total_passed=($checks | ForEach-Object { $_['passed'] } | Measure-Object -Sum).Sum;total_failed=0;
    protected_runtime_files_verified=$protected.Count;source_files_verified=$sourceHashes.Count;
    reproduced_original_exit_code=-1073741819;
    baseline_report='build/combat-crash-fix/baseline-repro-unsandboxed/manifest.json';
    limitation='Automated attack/display and animation scenarios on an unsaved original cave, not a full manual playthrough';
    changed_runtime_files=@('fallout-ce.exe');AGENTS_updated=$false
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'integration.json') -Encoding utf8
Write-Output "Installed tested combat fix: $hash"
Write-Output "Preserved $($protected.Count) other runtime files. Backup: $backup"
