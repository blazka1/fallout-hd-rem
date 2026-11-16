[CmdletBinding()]
param([string]$OutputDirectory = 'build/hd-world-pilot/wall-variant-fallback/v9')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$assets = Join-Path $runtime 'data/art/hd/world-pilot'
$expectedCount = (Get-Content -LiteralPath (Join-Path $assets 'manifest.json') -Raw | ConvertFrom-Json).asset_count - 1
$registry = Join-Path $assets 'variants.tsv'
$out = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (Test-Path -LiteralPath $out) { throw 'Existing test evidence preserved; choose a new output directory.' }
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Fallout is running; no changes made.' }
$registryBytes = [IO.File]::ReadAllBytes($registry)
$registryHash = (Get-FileHash -LiteralPath $registry).Hash
$lines = [IO.File]::ReadAllLines($registry)
$targetRow = @($lines | Where-Object { $_ -notmatch '^#' -and $_.Trim().Length -gt 0 })[0]
$fields = $targetRow -split '\s+'
$imagePath = Join-Path $assets $fields[3]
$imageBytes = [IO.File]::ReadAllBytes($imagePath)
$imageHash = (Get-FileHash -LiteralPath $imagePath).Hash
New-Item -ItemType Directory -Path (Join-Path $out 'backup') | Out-Null
[IO.File]::WriteAllBytes((Join-Path $out 'backup/variants.tsv'), $registryBytes)
[IO.File]::WriteAllBytes((Join-Path $out ('backup/' + $fields[3])), $imageBytes)
$priorSmoke = $env:FALLOUT_HD_WORLD_VARIANT_SMOKE
$reports = @()
$restored = $false
try {
    $env:FALLOUT_HD_WORLD_VARIANT_SMOKE = '1'
    foreach ($case in @('omitted-slot-control', 'missing-file', 'invalid-alpha', 'invalid-header', 'changed-silhouette')) {
        if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Fallout started during test; stopping before mutation.' }
        [IO.File]::WriteAllBytes($registry, $registryBytes)
        [IO.File]::WriteAllBytes($imagePath, $imageBytes)
        switch ($case) {
            'omitted-slot-control' {
                [IO.File]::WriteAllLines($registry, @($lines | Where-Object { $_ -ne $targetRow }), [Text.Encoding]::ASCII)
            }
            'missing-file' {
                $missingRow = ($fields[0..2] -join "`t") + "`tmissing-wall-variant.rgba"
                if (Test-Path -LiteralPath (Join-Path $assets 'missing-wall-variant.rgba')) { throw 'Fixture filename already exists.' }
                [IO.File]::WriteAllLines($registry, @($lines | ForEach-Object { if ($_ -eq $targetRow) { $missingRow } else { $_ } }), [Text.Encoding]::ASCII)
            }
            'invalid-alpha' {
                $bad = [byte[]]$imageBytes.Clone()
                $bad[23] = 127
                [IO.File]::WriteAllBytes($imagePath, $bad)
            }
            'invalid-header' {
                [IO.File]::WriteAllText($imagePath, 'corrupt fixture', [Text.Encoding]::ASCII)
            }
            'changed-silhouette' {
                $bad = [byte[]]$imageBytes.Clone()
                $width = [BitConverter]::ToUInt32($bad, 8)
                $alpha = [byte](255 - $bad[23])
                for ($y = 0; $y -lt 4; $y++) { for ($x = 0; $x -lt 4; $x++) {
                    $bad[20 + 4 * ($y * $width + $x) + 3] = $alpha
                } }
                [IO.File]::WriteAllBytes($imagePath, $bad)
            }
        }
        $caseOut = Join-Path $out $case
        & (Join-Path $PSScriptRoot 'test.ps1') -OutputDirectory $caseOut -ExpectedAssetCount $expectedCount | Out-File -LiteralPath (Join-Path $out ($case + '.log')) -Encoding utf8
        $result = Get-Content -LiteralPath (Join-Path $caseOut 'result.json') -Raw | ConvertFrom-Json
        if ($result.failed -ne 0 -or $result.wall_variants -ne 23) { throw "Variant fallback failed: $case" }
        $reports += [ordered]@{ name=$case; result=$result; output=$caseOut }
    }
} finally {
    [IO.File]::WriteAllBytes($imagePath, $imageBytes)
    [IO.File]::WriteAllBytes($registry, $registryBytes)
    $env:FALLOUT_HD_WORLD_VARIANT_SMOKE = $priorSmoke
    $restored = (Get-FileHash -LiteralPath $imagePath).Hash -eq $imageHash -and (Get-FileHash -LiteralPath $registry).Hash -eq $registryHash
    if (-not $restored) { throw 'Variant restore hash mismatch; use backup in test evidence.' }
}
& 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $PSScriptRoot 'verify-wall-variants.py') $out
if ($LASTEXITCODE -ne 0) { throw 'Variant control comparison failed.' }
Write-Output "Wall variant fallback verified: $out"
