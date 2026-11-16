param([switch]$Apply)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Split-Path (Split-Path $PSScriptRoot -Parent) -Parent))
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'installed-files.json') -Raw | ConvertFrom-Json
$backup=[IO.Path]::GetFullPath($manifest.backup)
function Checked-Path([string]$Base,[string]$Relative) {
    $resolved=[IO.Path]::GetFullPath((Join-Path $Base $Relative))
    if(-not $resolved.StartsWith($Base.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {throw "Unsafe rollback path: $resolved"}
    return $resolved
}
if(-not $backup.StartsWith($project+'\build\backups\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Backup is outside project backups'}
if(Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue){throw 'Close Fallout before rollback'}
foreach($entry in $manifest.after.PSObject.Properties) {
    $target=Checked-Path $project $entry.Name
    if(-not(Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw "Later changes detected; refusing to overwrite: $target"
    }
    $before=$manifest.before.PSObject.Properties[$entry.Name].Value
    if($null -ne $before) {
        $saved=Checked-Path $backup $entry.Name
        if((Get-FileHash -LiteralPath $saved).Hash.ToLowerInvariant() -ne $before){throw "Backup mismatch: $saved"}
    }
}
if(-not $Apply){Write-Output 'Rollback verified. No files changed. Use -Apply only when rollback is requested.';return}
foreach($entry in $manifest.after.PSObject.Properties) {
    $target=Checked-Path $project $entry.Name
    $before=$manifest.before.PSObject.Properties[$entry.Name].Value
    if($null -eq $before){Remove-Item -LiteralPath $target}
    else {Copy-Item -LiteralPath (Checked-Path $backup $entry.Name) -Destination $target -Force}
}
Write-Output 'Restored only player integration files. Other runtime assets and user settings preserved.'
