$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pack=Join-Path $root 'runtime/hd-world-pilot/data/art/hd/world-pilot'
$registry=Join-Path $pack 'cave-variety-assets.tsv'
$saved=[IO.File]::ReadAllBytes($registry)
$prior=$env:FALLOUT_HD_CAVE_FALLBACK_TEST
$corrupt=Join-Path $pack 'cave-corrupt-test.rgba'
if(Test-Path -LiteralPath $corrupt) {throw 'Fallback fixture already exists'}
try {
    $env:FALLOUT_HD_CAVE_FALLBACK_TEST='1'
    foreach($kind in @('missing','corrupt')) {
        if($kind -eq 'corrupt') {[IO.File]::WriteAllBytes($corrupt,[byte[]](0,1,2,3))}
        [IO.File]::WriteAllText($registry,"224 128 128 cave-$kind-test.rgba`n")
        & "$PSScriptRoot/test.ps1" -OutputDirectory (Join-Path $root "build/hd-cave-distribution-20261115/fallback-$kind") -ExpectedAssetCount 206
    }
} finally {
    [IO.File]::WriteAllBytes($registry,$saved)
    if(Test-Path -LiteralPath $corrupt) {Remove-Item -LiteralPath $corrupt}
    $env:FALLOUT_HD_CAVE_FALLBACK_TEST=$prior
}
