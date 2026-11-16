[CmdletBinding()]
param([string]$OutputDirectory = 'build/hd-world-pilot/decor-fallback/v11', [ValidateRange(240,248)][int]$AssetId = 240)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$assets = Join-Path $runtime 'data/art/hd/world-pilot'
$registry = Join-Path $assets 'decor.tsv'
$imageName = 'asset-{0:D3}.rgba' -f $AssetId
$imagePath = Join-Path $assets $imageName
$out = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (Test-Path -LiteralPath $out) { throw 'Use a new evidence directory.' }
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Fallout is running.' }
$registryBytes = [IO.File]::ReadAllBytes($registry)
$imageBytes = [IO.File]::ReadAllBytes($imagePath)
$registryHash = (Get-FileHash -LiteralPath $registry).Hash
$imageHash = (Get-FileHash -LiteralPath $imagePath).Hash
$lines = [IO.File]::ReadAllLines($registry)
$targetRow = @($lines | Where-Object { $_ -match ('^'+$AssetId+'\s') })[0]
$fields = $targetRow -split '\s+'
$expectedCount = (Get-Content -LiteralPath (Join-Path $assets 'manifest.json') -Raw | ConvertFrom-Json).asset_count - 1
New-Item -ItemType Directory -Path (Join-Path $out 'backup') | Out-Null
[IO.File]::WriteAllBytes((Join-Path $out 'backup/decor.tsv'), $registryBytes)
[IO.File]::WriteAllBytes((Join-Path $out ('backup/'+$imageName)), $imageBytes)
$priorSmoke = $env:FALLOUT_HD_WORLD_VARIANT_SMOKE
$reports = @()
$comparisons = @()
try {
    $env:FALLOUT_HD_WORLD_VARIANT_SMOKE = '1'
    foreach ($case in @('omitted-asset-control','missing-file','invalid-alpha','invalid-header')) {
        if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Fallout started; stopping fixture changes.' }
        [IO.File]::WriteAllBytes($registry, $registryBytes)
        [IO.File]::WriteAllBytes($imagePath, $imageBytes)
        switch ($case) {
            'omitted-asset-control' {
                [IO.File]::WriteAllLines($registry, @($lines | Where-Object { $_ -ne $targetRow }), [Text.Encoding]::ASCII)
            }
            'missing-file' {
                if (Test-Path -LiteralPath (Join-Path $assets 'missing-decor.rgba')) { throw 'Fixture file already exists.' }
                $missingRow = ($fields[0..2] -join "`t") + "`tmissing-decor.rgba"
                [IO.File]::WriteAllLines($registry, @($lines | ForEach-Object { if ($_ -eq $targetRow) { $missingRow } else { $_ } }), [Text.Encoding]::ASCII)
            }
            'invalid-alpha' {
                $bad = [byte[]]$imageBytes.Clone(); $bad[23] = 127
                [IO.File]::WriteAllBytes($imagePath, $bad)
            }
            'invalid-header' { [IO.File]::WriteAllText($imagePath, 'invalid decoration', [Text.Encoding]::ASCII) }
        }
        $caseOut = Join-Path $out $case
        & (Join-Path $PSScriptRoot 'test.ps1') -OutputDirectory $caseOut -ExpectedAssetCount $expectedCount | Out-File -LiteralPath (Join-Path $out ($case+'.log')) -Encoding utf8
        $result = Get-Content -LiteralPath (Join-Path $caseOut 'result.json') -Raw | ConvertFrom-Json
        if ($result.failed -ne 0 -or $result.loaded_resources -ne $expectedCount) { throw "Failed: $case" }
        $reports += [ordered]@{ name=$case; result=$result; output=$caseOut }
        if ($case -ne 'omitted-asset-control') {
            foreach ($file in @('entrance-hd.bmp','wall-variants-enabled.bmp','entrance-classic.bmp')) {
                $controlHash = (Get-FileHash -LiteralPath (Join-Path $out ('omitted-asset-control/'+$file))).Hash
                $actualHash = (Get-FileHash -LiteralPath (Join-Path $caseOut $file)).Hash
                if ($controlHash -ne $actualHash) { throw "$case differs from omitted-asset control: $file" }
                $comparisons += "$case/$file equals omitted-asset control"
            }
        }
    }
} finally {
    [IO.File]::WriteAllBytes($registry, $registryBytes)
    [IO.File]::WriteAllBytes($imagePath, $imageBytes)
    $env:FALLOUT_HD_WORLD_VARIANT_SMOKE = $priorSmoke
    if ((Get-FileHash -LiteralPath $registry).Hash -ne $registryHash -or (Get-FileHash -LiteralPath $imagePath).Hash -ne $imageHash) { throw 'Restore hash mismatch.' }
}
$passed = ($reports | ForEach-Object { $_.result.passed } | Measure-Object -Sum).Sum + $comparisons.Count
[ordered]@{ executable_sha256=(Get-FileHash -LiteralPath (Join-Path $runtime 'fallout-ce.exe')).Hash; cases=$reports;
    comparisons=$comparisons; passed=$passed; failed=0; restored_and_hash_verified=$true
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'manifest.json') -Encoding utf8
Write-Output "Decoration fallback: $passed PASS, 0 FAIL. Restored and hash verified."
