[CmdletBinding()]
param([ValidateSet('missing-frame','corrupt-frame','missing-aimed','corrupt-aimed')][string]$Case)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$package=Join-Path $root 'runtime/hd-world-pilot/data/art/hd/critter-rat'
if(Get-Process fallout-ce -ErrorAction SilentlyContinue){throw 'Another Fallout instance is running; preserved.'}
$aimed=$Case -like '*aimed';$filename=if($aimed){'aimed.rgba'}else{'u0048.rgba'}
$path=Join-Path $package $filename;$bytes=[IO.File]::ReadAllBytes($path);$hash=(Get-FileHash $path).Hash
$expected=540
if(-not $aimed){
    $lost=@(Get-Content (Join-Path $package 'registry.tsv') | Where-Object {$_ -match ('\s'+[regex]::Escape($filename)+'$')}).Count
    if($lost -lt 1){throw 'Frame not registered.'};$expected-=$lost
}
try {
    if($Case -like 'missing-*'){Remove-Item -LiteralPath $path}
    else {[IO.File]::WriteAllBytes($path,[Text.Encoding]::ASCII.GetBytes('invalid HD rat test frame'))}
    & (Join-Path $PSScriptRoot 'test.ps1') -Mode rat -ExpectedKeys $expected -ExpectedAimed $(if($aimed){0}else{1}) -OutputDirectory "build/hd-rat-world-integration-20261115/verified/$Case"
} finally {
    [IO.File]::WriteAllBytes($path,$bytes)
    if((Get-FileHash $path).Hash -ne $hash){throw 'Rat fallback test file did not restore.'}
}
