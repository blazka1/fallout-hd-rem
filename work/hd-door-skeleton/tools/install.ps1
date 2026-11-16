param([switch]$AssetsOnly, [string]$PackageDirectory='assets/hd/v13ent-door-skeleton/v5-balanced-shadow-x4')
$ErrorActionPreference = 'Stop'
$skeletonRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$skeletonPackage = Join-Path $skeletonRoot $PackageDirectory
$skeletonRuntime = Join-Path $skeletonRoot 'runtime/hd-world-pilot'
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Close Fallout before updating its runtime.' }
$skeletonManifest = Get-Content -LiteralPath (Join-Path $skeletonPackage 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $skeletonPackage 'v13bones.rgba')).Hash -ne $skeletonManifest.rgba_sha256) { throw 'Skeleton payload hash mismatch' }
$skeletonExe = Join-Path $skeletonRoot 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
if (-not $AssetsOnly -and -not (Test-Path -LiteralPath $skeletonExe)) { throw 'Build pilot first' }
$skeletonDestination = Join-Path $skeletonRuntime 'data/art/hd/v13bones'
New-Item -ItemType Directory -Force -Path $skeletonDestination | Out-Null
foreach ($skeletonFile in @('v13bones.rgba','manifest.json')) {
    Copy-Item -LiteralPath (Join-Path $skeletonPackage $skeletonFile) -Destination (Join-Path $skeletonDestination $skeletonFile) -Force
}
if (-not $AssetsOnly) { Copy-Item -LiteralPath $skeletonExe -Destination (Join-Path $skeletonRuntime 'fallout-ce.exe') -Force }
$skeletonConfig = Join-Path $skeletonRuntime 'fallout.cfg'
$skeletonText = [IO.File]::ReadAllText($skeletonConfig)
if ($skeletonText -match '(?m)^hd_v13_skeleton=') { $skeletonText = [regex]::Replace($skeletonText, '(?m)^hd_v13_skeleton=[^\r\n]*', 'hd_v13_skeleton=1') }
else { $skeletonText = [regex]::Replace($skeletonText, '(?m)^\[remaster\]\r?\n', "[remaster]`r`nhd_v13_skeleton=1`r`n") }
[IO.File]::WriteAllText($skeletonConfig,$skeletonText,[Text.Encoding]::ASCII)
if ($AssetsOnly) { Write-Output 'Installed skeleton asset; pilot EXE, other packages and saves retained.' }
else { Write-Output 'Installed skeleton and pilot EXE; existing cave/player/menu packages and saves retained.' }
