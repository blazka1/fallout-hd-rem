[CmdletBinding()]
param([ValidateSet('missing-frame','corrupt-frame','missing-aimed','corrupt-aimed')][string]$Case,[string]$OutputSuffix='')
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$package=Join-Path $root 'runtime/hd-rat-pilot/data/art/hd/critter-rat'
if(Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) {throw 'Another Fallout instance is running; preserved.'}
$aimed=$Case -like '*aimed'
$filename=if($aimed){'aimed.rgba'}else{'u0048.rgba'}
$path=Join-Path $package $filename
$bytes=[IO.File]::ReadAllBytes($path)
$hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
$expected=540
if(-not $aimed){
    $lost=@(Get-Content -LiteralPath (Join-Path $package 'registry.tsv') | Where-Object {$_ -match ('\s'+[regex]::Escape($filename)+'$')}).Count
    if($lost -lt 1){throw 'Fallback frame is not registered.'}
    $expected-=$lost
}
try {
    if($Case -like 'missing-*'){Remove-Item -LiteralPath $path}
    else {[IO.File]::WriteAllBytes($path,[Text.Encoding]::ASCII.GetBytes('invalid HD rat test frame'))}
    $expectedAim=if($aimed){0}else{1}
    & (Join-Path $PSScriptRoot 'test.ps1') -ExpectedKeys $expected -ExpectedAimed $expectedAim -OutputDirectory "build/hd-rat-20261115/preview/$Case$OutputSuffix" -TimeoutSeconds 900
} finally {
    [IO.File]::WriteAllBytes($path,$bytes)
    if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $hash){throw 'Own isolated fallback test file did not restore byte-for-byte.'}
}
