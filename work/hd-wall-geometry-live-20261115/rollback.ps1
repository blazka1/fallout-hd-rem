param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$backup=Join-Path $root 'build/backups/before-wall-geometry-live-20261115'
$state=Get-Content -LiteralPath (Join-Path $backup 'state.json') -Raw | ConvertFrom-Json
if($state.status -ne 'installed') {throw 'The component is not recorded as installed.'}
if(-not $CheckOnly -and (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue)) {throw 'Close Fallout before rollback.'}
foreach($f in $state.files) {
    $target=[IO.Path]::GetFullPath((Join-Path $root $f.path))
    if(-not $target.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid target path.'}
    $current=if(Test-Path -LiteralPath $target -PathType Leaf) {(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()} else {$null}
    if($current -ne $f.installed_sha256) {throw "File changed after installation; preserve later work: $target"}
    if($f.existed) {
        $saved=Join-Path $backup $f.path
        if((Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $f.before_sha256) {throw "Backup verification failed: $saved"}
    }
}
if($CheckOnly) {Write-Output "Rollback verified for $($state.files.Count) files; nothing changed.";return}
foreach($f in $state.files) {
    $target=[IO.Path]::GetFullPath((Join-Path $root $f.path))
    if($f.existed) {
        Copy-Item -LiteralPath (Join-Path $backup $f.path) -Destination $target -Force
        if([IO.Path]::GetExtension($target) -in '.cc','.h','.inc') {(Get-Item -LiteralPath $target).LastWriteTime=Get-Date}
    } elseif(Test-Path -LiteralPath $target -PathType Leaf) {Remove-Item -LiteralPath $target}
}
Write-Output 'Previous cave assets, source and EXE restored. Save games and configuration were not changed.'
