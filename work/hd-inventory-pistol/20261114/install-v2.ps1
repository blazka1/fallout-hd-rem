[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TestManifest)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime = Join-Path $project 'runtime/hd-world-pilot'
$source = Join-Path $project 'assets/hd/inventory/10mm-pistol/v2/pistol.rgba'
$target = Join-Path $runtime 'data/art/hd/inventory/10mm-pistol/pistol.rgba'
$exe = Join-Path $runtime 'fallout-ce.exe'
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Write-Json([string]$Path,$Object) { $Object | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding utf8 }
function Assert-Stopped {
 $boundary=[IO.Path]::GetFullPath($runtime).TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
 foreach($process in Get-Process) {
  $processPath=$null
  try { $processPath=$process.Path } catch {}
  if($processPath -and $processPath.StartsWith($boundary,[StringComparison]::OrdinalIgnoreCase)) { throw "Close Fallout before installation: PID $($process.Id). No process was stopped." }
 }
}
$manifestPath=(Resolve-Path -LiteralPath $TestManifest).Path
$test=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if([int]$test.item_pid -ne 8 -or [int]$test.expected_loaded -ne 1 -or [int]$test.exit_code -ne 0 -or [int]$test.result.failed -ne 0 -or [int]$test.result.passed -le 0) { throw 'Require successful PID8 loaded candidate test.' }
$exeHash=Hash $exe
$sourceHash=Hash $source
if($exeHash -ne $test.executable_sha256 -or $sourceHash -ne $test.asset_sha256) { throw 'Candidate EXE or asset hash differs from successful test.' }
$bytes=[IO.File]::ReadAllBytes($source)
if($bytes.Length -ne (20+280*252*4) -or [Text.Encoding]::ASCII.GetString($bytes,0,4) -ne 'F1HD' -or [BitConverter]::ToUInt32($bytes,4) -ne 1 -or [BitConverter]::ToUInt32($bytes,8) -ne 280 -or [BitConverter]::ToUInt32($bytes,12) -ne 252 -or [BitConverter]::ToUInt32($bytes,16) -ne 4) { throw 'Invalid F1HD RGBA8 280x252.' }
Assert-Stopped
$preserved=[ordered]@{}
foreach($path in @($exe,(Join-Path $runtime 'data/art/hd/inventory/knife/knife.rgba'),(Join-Path $runtime 'data/art/hd/inventory/brass-knuckles/knuckles.rgba'))) { $preserved[$path]=Hash $path }
$oldHash=Hash $target
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backup=Join-Path $project ('build/backups/before-pistol-v2-asset-'+$stamp)
New-Item -ItemType Directory -Path $backup | Out-Null
$backupAsset=Join-Path $backup 'pistol.rgba'
Copy-Item -LiteralPath $target -Destination $backupAsset
if((Hash $backupAsset) -ne $oldHash) { throw 'Backup hash mismatch.' }
Write-Json (Join-Path $backup 'backup.json') ([ordered]@{created_utc=[DateTime]::UtcNow.ToString('o');target=$target;old_sha256=$oldHash;new_sha256=$sourceHash;preserved=$preserved;test_manifest=$manifestPath})
Assert-Stopped
if((Hash $target) -ne $oldHash -or (Hash $source) -ne $sourceHash) { throw 'Asset changed before commit; refusing overwrite.' }
try {
 Copy-Item -LiteralPath $source -Destination $target -Force
 if((Hash $target) -ne $sourceHash) { throw 'Installed hash mismatch.' }
 foreach($entry in $preserved.GetEnumerator()) { if((Hash $entry.Key) -ne $entry.Value) { throw "Preserved file changed: $($entry.Key)" } }
} catch {
 Copy-Item -LiteralPath $backupAsset -Destination $target -Force
 throw
}
$receipts=Join-Path $project 'build/hd-inventory-pistol/v2-20261114/installations'
New-Item -ItemType Directory -Force -Path $receipts | Out-Null
$receipt=Join-Path $receipts ($stamp+'.json')
Write-Json $receipt ([ordered]@{status='installed_and_hash_verified';installed_utc=[DateTime]::UtcNow.ToString('o');source=$source;target=$target;sha256=$sourceHash;previous_sha256=$oldHash;executable_sha256=$exeHash;backup_asset=$backupAsset;preserved=$preserved;test_manifest=$manifestPath;test_manifest_sha256=(Hash $manifestPath);scope='Only pistol.rgba replaced; EXE, other art, configuration, DAT and saves unchanged.'})
Write-Output "Installed pistol v2 asset. Receipt: $receipt"
