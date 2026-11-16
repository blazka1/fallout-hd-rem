$ErrorActionPreference = 'Stop'
$skeletonRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$skeletonAsset = [IO.Path]::GetFullPath((Join-Path $skeletonRoot 'runtime/hd-world-pilot/data/art/hd/v13bones/v13bones.rgba'))
$skeletonHeld = $skeletonAsset + '.fallback-check-held'
$skeletonScope = [IO.Path]::GetFullPath((Join-Path $skeletonRoot 'runtime/hd-world-pilot/data/art/hd/v13bones')) + [IO.Path]::DirectorySeparatorChar
if (-not $skeletonAsset.StartsWith($skeletonScope) -or -not $skeletonHeld.StartsWith($skeletonScope)) { throw 'Unexpected fallback target' }
if ((Get-Process fallout-ce -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath $skeletonHeld)) { throw 'Runtime busy or prior fallback hold exists' }
$skeletonHash = (Get-FileHash -LiteralPath $skeletonAsset).Hash
$skeletonOldExpect = $env:FALLOUT_HD_SKELETON_EXPECT
$skeletonReportRoot = Join-Path $skeletonRoot 'build/hd-door-skeleton/fallback-v18'
New-Item -ItemType Directory -Force -Path $skeletonReportRoot | Out-Null
Move-Item -LiteralPath $skeletonAsset -Destination $skeletonHeld
try {
    $env:FALLOUT_HD_SKELETON_EXPECT = '0'
    & (Join-Path $skeletonRoot 'work/hd-player-male/tools/test-player.ps1') -OutputDirectory (Join-Path $skeletonReportRoot 'missing') *> (Join-Path $skeletonReportRoot 'missing.log')
    # Deliberately invalid small payload owned by this test; original is held intact.
    [IO.File]::WriteAllBytes($skeletonAsset,[Text.Encoding]::ASCII.GetBytes('invalid test payload'))
    & (Join-Path $skeletonRoot 'work/hd-player-male/tools/test-player.ps1') -OutputDirectory (Join-Path $skeletonReportRoot 'corrupt') *> (Join-Path $skeletonReportRoot 'corrupt.log')
} finally {
    if (Test-Path -LiteralPath $skeletonAsset) { Remove-Item -LiteralPath $skeletonAsset }
    Move-Item -LiteralPath $skeletonHeld -Destination $skeletonAsset
    $env:FALLOUT_HD_SKELETON_EXPECT = $skeletonOldExpect
}
if ((Get-FileHash -LiteralPath $skeletonAsset).Hash -ne $skeletonHash) { throw 'Restored skeleton hash mismatch' }
Get-Content -LiteralPath (Join-Path $skeletonReportRoot 'missing/result.json'),(Join-Path $skeletonReportRoot 'corrupt/result.json')
Write-Output 'Missing and malformed payload fallback checks completed; original skeleton restored byte-exact.'
