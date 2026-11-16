[CmdletBinding()]
param([string]$FixtureParent=(Join-Path (Split-Path $PSScriptRoot -Parent) 'build/retention-self-test'))
$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot 'complete-build-check.ps1'
$root=Join-Path $FixtureParent ('fixture-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path (Join-Path $root 'build') -Force
Add-Type -AssemblyName System.Drawing
$script:checks=0
function Check($value,[string]$message) {if(-not $value){throw "FAIL: $message"}; $script:checks++; Write-Output "PASS: $message"}
function Make-Run([string]$name,[Drawing.Color]$color=[Drawing.Color]::Red) {
    $dir=Join-Path $root ('build/tests/'+$name);New-Item -ItemType Directory -Path $dir -Force|Out-Null
    $bmp=[Drawing.Bitmap]::new(13,7)
    try {$g=[Drawing.Graphics]::FromImage($bmp);try{$g.Clear($color)}finally{$g.Dispose()};$bmp.Save((Join-Path $dir 'capture.bmp'),[Drawing.Imaging.ImageFormat]::Bmp)}finally{$bmp.Dispose()}
    'report'|Set-Content -LiteralPath (Join-Path $dir 'checks.txt')
    return $dir
}
function Run-Helper([string]$dir,[string]$component='test',[string]$outcome='Passed',[string]$backup='') {
    & $helper -ProjectRoot $root -RunDirectory $dir -Component $component -Outcome $outcome -BackupDirectory $backup
}
$first=Make-Run 'one'
Run-Helper $first
Check ((Test-Path (Join-Path $first 'capture.png')) -and -not (Test-Path (Join-Path $first 'capture.bmp'))) 'lossless PNG replaces BMP'
$second=Make-Run 'failure'
Run-Helper $second 'test' 'Failed'
Check (Test-Path (Join-Path $first 'capture.png')) 'failure retains last successful capture'
$third=Make-Run 'three' ([Drawing.Color]::Blue)
Run-Helper $third
Check (-not (Test-Path (Join-Path $first 'capture.png'))) 'success rotates old registered PNG'
Check (-not (Test-Path (Join-Path $second 'capture.png'))) 'success resolves preceding failed capture'
Check ((Test-Path (Join-Path $first 'checks.txt')) -and (Test-Path (Join-Path $first 'retention-manifest.json'))) 'old reports remain'
''|Set-Content -LiteralPath (Join-Path $third '.keep-build-artifacts')
$fourth=Make-Run 'four'
Run-Helper $fourth
Check (Test-Path (Join-Path $third 'capture.png')) 'explicit pin survives rotation'
$fifth=Make-Run 'five'
# A changed old capture must be preserved even though its recorded version expired.
[IO.File]::AppendAllText((Join-Path $fourth 'capture.png'),'changed')
Run-Helper $fifth
Check (Test-Path (Join-Path $fourth 'capture.png')) 'changed file is preserved'
$child=Make-Run 'five/child'
$rejected=$false;try{Run-Helper $child 'other'}catch{$rejected=$true}
Check $rejected 'cross-component parent/child run rejected'
Check (Test-Path (Join-Path $child 'capture.bmp')) 'rejection preserves input'
$sixth=Make-Run 'six'
$protected=Join-Path $sixth 'runtime/data'
New-Item -ItemType Directory -Path $protected -Force|Out-Null
Copy-Item -LiteralPath (Join-Path $sixth 'capture.bmp') -Destination (Join-Path $protected 'asset.bmp')
Run-Helper $sixth
Check (Test-Path (Join-Path $protected 'asset.bmp')) 'nested runtime asset excluded'
$bad=Make-Run 'mismatched'
Copy-Item -LiteralPath (Join-Path $third 'capture.png') -Destination (Join-Path $bad 'capture.png')
$rejected=$false;try{Run-Helper $bad 'bad'}catch{$rejected=$true}
Check $rejected 'different unowned PNG rejected'
Check (Test-Path (Join-Path $bad 'capture.bmp')) 'mismatched BMP retained'
$rejected=$false;try{& $helper -ProjectRoot $root -RunDirectory $PSScriptRoot -Component outside -Outcome Passed}catch{$rejected=$true}
Check $rejected 'outside-build path rejected'
$dep=Join-Path $root 'build/fallout1-ce/_deps/test';New-Item -ItemType Directory -Path $dep -Force|Out-Null
$rejected=$false;try{Run-Helper $dep 'deps'}catch{$rejected=$true}
Check $rejected 'dependency directory rejected'
$backups=@()
foreach($n in 1,2) {
    $b=Join-Path $root "build/backups/test-$n";New-Item -ItemType Directory -Path (Join-Path $b 'SAVEGAME') -Force|Out-Null
    [IO.File]::WriteAllBytes((Join-Path $b 'old.exe'),[byte[]](1,2,3))
    'source'|Set-Content (Join-Path $b 'source.cc');'save'|Set-Content (Join-Path $b 'SAVEGAME/SAVE.DAT');'report'|Set-Content (Join-Path $b 'manifest.json')
    $backups+=$b
    $r=Make-Run "rollback-check-$n";Run-Helper $r 'backup-test' 'Passed' $b
}
Check (-not (Test-Path (Join-Path $backups[0] 'old.exe'))) 'older registered backup binary rotates'
Check (Test-Path (Join-Path $backups[1] 'old.exe')) 'latest rollback binary retained'
Check ((Test-Path (Join-Path $backups[0] 'source.cc')) -and (Test-Path (Join-Path $backups[0] 'SAVEGAME/SAVE.DAT')) -and (Test-Path (Join-Path $backups[0] 'manifest.json'))) 'backup source, saves and reports retained'
$temp=Join-Path $r 'probe.exe';[IO.File]::WriteAllBytes($temp,[byte[]](4,5,6))
& $helper -ProjectRoot $root -RunDirectory $r -Component 'backup-test' -Outcome Passed -TemporaryFiles $temp
Check (-not (Test-Path $temp)) 'declared temporary executable removed'
Run-Helper $r 'backup-test'
Check (Test-Path (Join-Path $r 'capture.png')) 'finalization is idempotent'
$null=Make-Run 'rollback-check-2' ([Drawing.Color]::Green)
Run-Helper $r 'backup-test'
Check (-not (Test-Path (Join-Path $r 'capture.bmp'))) 'rerun replaces only its previously owned PNG'
$empty=Join-Path $root 'build/tests/empty';New-Item -ItemType Directory -Path $empty -Force|Out-Null
$rejected=$false;try{Run-Helper $empty 'backup-test'}catch{$rejected=$true}
Check ($rejected -and (Test-Path (Join-Path $r 'capture.png'))) 'empty run cannot discard previous valid captures'
$linked=Make-Run 'junction-test'
$link=Join-Path $linked 'outside-link'
New-Item -ItemType Junction -Path $link -Target $PSScriptRoot|Out-Null
$rejected=$false;try{Run-Helper $linked 'junction'}catch{$rejected=$true}
Check $rejected 'junction subtree rejected'
Remove-Item -LiteralPath $link -Force
$corruptState=Join-Path $root 'build/.retention/corrupt.json'
@{component='corrupt';runs=@(@{directory=$dep;captures=@()});backup=$null}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $corruptState
$rejected=$false;try{Run-Helper $r 'backup-test'}catch{$rejected=$true}
Check $rejected 'protected path in old registry rejected'
[ordered]@{passed=$script:checks;failed=0;fixture=$root}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $FixtureParent 'test-result.json') -Encoding utf8
Write-Output "TOTAL: $script:checks PASS, 0 FAIL"
