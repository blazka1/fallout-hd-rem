param([string]$ProjectRoot='C:/Users/Administrator/Desktop/Fallout1-Godot')
$ErrorActionPreference='Stop'
$component=Join-Path $ProjectRoot 'work/hd-wall-grey-match-20261116'
$exe=Join-Path $component 'runtime/fallout-ce.exe'
$testExe=Join-Path $ProjectRoot 'build/hd-wall-original-restore-20261116/test-msvc/RelWithDebInfo/fallout-ce.exe'
$stock=Join-Path $component 'stock-executable.bin'
if(Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue){throw 'Close Fallout before test.'}
if((Get-FileHash -LiteralPath $exe).Hash -ne (Get-FileHash -LiteralPath (Join-Path $ProjectRoot 'runtime/hd-world-pilot/fallout-ce.exe')).Hash){throw 'Expected the unchanged live EXE in isolated runtime.'}
if(Test-Path -LiteralPath $stock){
 if((Get-FileHash -LiteralPath $stock).Hash -ne (Get-FileHash -LiteralPath $exe).Hash){throw 'Different existing stock EXE backup.'}
} else {Copy-Item -LiteralPath $exe -Destination $stock}
try {
 Copy-Item -LiteralPath $testExe -Destination $exe -Force
 & (Join-Path $component 'test.ps1') -ProjectRoot $ProjectRoot -OutputDirectory (Join-Path $ProjectRoot 'build/hd-wall-grey-match-20261116/after-v1')
} finally {
 Copy-Item -LiteralPath $stock -Destination $exe -Force
}
& (Join-Path $ProjectRoot 'scripts/complete-build-check.ps1') -ProjectRoot $ProjectRoot -RunDirectory (Join-Path $ProjectRoot 'build/hd-wall-grey-match-20261116/after-v1') -Component 'walls-grey' -Outcome Passed
