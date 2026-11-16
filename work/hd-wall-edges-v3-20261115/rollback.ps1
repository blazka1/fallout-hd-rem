param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$backup=Join-Path $root 'build/backups/before-wall-edges-v3-20261115'
$live=Join-Path $root 'runtime/hd-world-pilot/data/art/hd/world-pilot'
$state=Get-Content -LiteralPath (Join-Path $backup 'state.json') -Raw | ConvertFrom-Json
if($state.status -ne 'installed') {throw 'No completed installation recorded.'}
if(-not $CheckOnly -and (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue)) {throw 'Close Fallout before rollback.'}
foreach($f in $state.files) {
    if([IO.Path]::GetFileName($f.name) -ne $f.name) {throw 'Unsafe filename.'}
    $target=[IO.Path]::GetFullPath((Join-Path $live $f.name))
    if(-not $target.StartsWith($live+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe target.'}
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $f.installed_sha256) {throw "Later changes detected: $target"}
    if((Get-FileHash -LiteralPath (Join-Path $backup $f.name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $f.before_sha256) {throw 'Backup hash mismatch.'}
}
if($CheckOnly) {Write-Output "Rollback verified for $($state.files.Count) files; nothing changed.";return}
foreach($f in $state.files) {Copy-Item -LiteralPath (Join-Path $backup $f.name) -Destination (Join-Path $live $f.name) -Force}
Write-Output 'Restored previous wall geometry assets and metadata. EXE, saves and settings unchanged.'
