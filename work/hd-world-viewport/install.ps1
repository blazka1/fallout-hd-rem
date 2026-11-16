[CmdletBinding()]
param([string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent))
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$output = Join-Path $root 'build/hd-world-viewport'
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$source = Join-Path $root 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
$target = Join-Path $runtime 'fallout-ce.exe'
$backup = Join-Path $root 'build/backups/before-full-height-world-20261114'
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) { throw 'Close Fallout before installation.' }
$candidateHash = (Get-FileHash -LiteralPath $source).Hash
$oldHash = (Get-FileHash -LiteralPath $target).Hash
if ($oldHash -ne (Get-FileHash -LiteralPath (Join-Path $backup 'runtime/hd-world-pilot/fallout-ce.exe')).Hash) {
    throw 'Installed executable changed since backup; inspect the newer installation before replacing it.'
}
$reports = @()
$total = 0
foreach ($name in @('world-v1','hud-v1','menu-v1','classic-640-v1','1440p-v1','ultrawide-v1','disabled-v1','player-v1','performance-after-v1')) {
    $path = Join-Path $output "$name/manifest.json"
    $report = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $counts = if ($name -eq 'player-v1') { $report.result } else { $report }
    if ($report.executable_sha256 -ne $candidateHash -or $report.exit_code -ne 0 -or $counts.failed -ne 0 -or $counts.passed -le 0) {
        throw "No passing report for candidate: $name"
    }
    $total += $counts.passed
    $reports += [ordered]@{report="build/hd-world-viewport/$name/manifest.json";passed=$counts.passed;failed=$counts.failed}
}
$pixels = Get-Content -LiteralPath (Join-Path $output 'pixel-comparison.json') -Raw | ConvertFrom-Json
if (-not $pixels.passed -or $pixels.upper_world.changed -ne 0 -or $pixels.hud.changed -ne 0) { throw 'Pixel comparison failed.' }
$sourceHashes = Get-Content -LiteralPath (Join-Path $root 'build/hd-world-pilot/logs/source-hashes.json') -Raw | ConvertFrom-Json
foreach ($file in $sourceHashes) {
    if ((Get-FileHash -LiteralPath (Join-Path $root ('work/hd-world-pilot/fallout1-ce-main/' + $file.path))).Hash -ne $file.sha256) {
        throw "Source changed after compilation: $($file.path)"
    }
}
$art = Get-Content -LiteralPath (Join-Path $output 'verified-runtime-art.json') -Raw | ConvertFrom-Json
foreach ($file in $art) {
    if ((Get-FileHash -LiteralPath (Join-Path $runtime ('data/art/' + $file.path))).Hash -ne $file.sha256) {
        throw "Artwork changed after testing: $($file.path)"
    }
}
# Hash all non-executable runtime files, including the user's configuration/saves.
$protected = @(Get-ChildItem -LiteralPath $runtime -Recurse -File | Where-Object { $_.FullName -ne $target } | ForEach-Object {
    [ordered]@{path=$_.FullName;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash}
})
Copy-Item -LiteralPath $source -Destination $target -Force
if ((Get-FileHash -LiteralPath $target).Hash -ne $candidateHash) { throw 'Installed executable hash mismatch.' }
foreach ($file in $protected) {
    if ((Get-FileHash -LiteralPath $file.path).Hash -ne $file.sha256) { throw "Protected runtime file changed: $($file.path)" }
}
$before = Get-Content -LiteralPath (Join-Path $output 'performance-before-v1/benchmark.json') -Raw | ConvertFrom-Json
$after = Get-Content -LiteralPath (Join-Path $output 'performance-after-v1/benchmark.json') -Raw | ConvertFrom-Json
$performance = @($after.rows | Where-Object { $_.mode -eq 'hd_enabled' -and $_.workload -in @('full_world_refresh','incremental_scroll') } | ForEach-Object {
    $row = $_
    $previous = $before.rows | Where-Object { $_.mode -eq $row.mode -and $_.workload -eq $row.workload -and $_.requested_width -eq $row.requested_width }
    [ordered]@{width=$row.requested_width;workload=$row.workload;before_median_ms=$previous.median_ms;after_median_ms=$row.median_ms}
})
[ordered]@{
    status='installed-and-verified';completed_utc=[DateTime]::UtcNow.ToString('o');
    scope='Full-height world beside centered HUD; preserved camera center; visible-window input and full-buffer scrolling';
    runtime='runtime/hd-world-pilot';executable_sha256=$candidateHash;previous_executable_sha256=$oldHash;
    backup='build/backups/before-full-height-world-20261114';
    fresh_passed=$total;fresh_failed=0;reports=$reports;pixel_comparison=$pixels;
    tested_art_files=$art.Count;protected_runtime_files_verified=$protected.Count;
    performance=$performance;performance_scope='24 hidden-window CPU samples per workload; not gameplay FPS';
    visual_review=@('world-v1/entrance-hd.png','player-v1/player-hd-cave-hd.png');
    launcher='Start-Fallout-HD-World-Pilot.cmd';setting='[remaster] full_height_world=1 (default); 0 restores old viewport after restart';
    limits='Automated rendering, input, movement and regression checks; not a full manual playthrough';
    AGENTS_updated=$false
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'integration.json') -Encoding utf8
$statePath = Join-Path $root 'work/hd-world-viewport/task.json'
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$state.status='installed-and-verified'
$state.updated_utc=[DateTime]::UtcNow.ToString('o')
$state.installed_sha256=$candidateHash
$state.pending=@()
$state.runtime_updated=$true
$state | Add-Member -NotePropertyName report -NotePropertyValue 'build/hd-world-viewport/integration.json' -Force
$state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding utf8
Write-Output "Installed $candidateHash; $total fresh checks passed; $($protected.Count) other runtime files preserved."
