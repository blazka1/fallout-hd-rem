param([ValidateSet('Candidates','Installed')][string]$Stage = 'Candidates')
$ErrorActionPreference = 'Stop'
$project = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $project
$reportRoot = Join-Path $project 'build/hd-inventory-10mm-ammo'
$runtime = Join-Path $project 'runtime/hd-world-pilot'
$buildExe = Join-Path $project 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
$hash = (Get-FileHash -LiteralPath $buildExe).Hash
if (Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue) { throw 'A game/test process is running. Wait without stopping it.' }
if ($Stage -eq 'Candidates') {
    $buildManifest = Get-Content build/hd-world-pilot/logs/build-manifest.json -Raw | ConvertFrom-Json
    if ($buildManifest.executable_sha256 -ne $hash) { throw 'Build manifest does not match EXE.' }
    $snapshot = Get-Content build/hd-world-pilot/logs/source-hashes.json -Raw | ConvertFrom-Json
    foreach ($file in $snapshot) {
        $source = Join-Path 'work/hd-world-pilot/fallout1-ce-main' $file.path
        if ((Get-FileHash -LiteralPath $source).Hash -ne $file.sha256) { throw "Source changed after build: $source" }
    }
    $exe = Join-Path $runtime 'fallout-ammo-test.exe'
    Copy-Item -LiteralPath $buildExe -Destination $exe -Force
    foreach ($item in @(@{pid=29;key='jhp'},@{pid=30;key='ap'})) {
        foreach ($mode in @('loaded','missing','corrupt')) {
            $name = 'final-' + $item.key + '-' + $mode
            $output = Join-Path $reportRoot ('preview/' + $name)
            if (Test-Path -LiteralPath $output) { throw "Preserve previous report: $output" }
            $asset = switch ($mode) {
                'loaded' { Join-Path $project ('assets/hd/inventory/10mm-' + $item.key + '/v1/ammo.rgba') }
                'missing' { Join-Path $reportRoot 'missing.rgba' }
                'corrupt' { Join-Path $reportRoot 'fixtures/corrupt.rgba' }
            }
            $expected = if ($mode -eq 'loaded') { 1 } else { 0 }
            & "$PSScriptRoot/test.ps1" -ItemPid $item.pid -Executable $exe -AssetPath $asset -ExpectedLoaded $expected -OutputDirectory $output *> (Join-Path $reportRoot ($name + '.log'))
            $result = Get-Content (Join-Path $output 'result.json') -Raw | ConvertFrom-Json
            Write-Output "$name : $($result.passed) PASS / $($result.failed) FAIL"
        }
    }
} else {
    if ((Get-FileHash (Join-Path $runtime 'fallout-ce.exe')).Hash -ne $hash) { throw 'Installed EXE does not match build.' }
    foreach ($item in @(@{pid=4;key='knife'},@{pid=8;key='pistol'},@{pid=21;key='knuckles'})) {
        $name = 'final-' + $item.key
        $output = Join-Path $reportRoot ('preview/' + $name)
        if (Test-Path -LiteralPath $output) { throw "Preserve previous report: $output" }
        & "$PSScriptRoot/test.ps1" -ItemPid $item.pid -OutputDirectory $output *> (Join-Path $reportRoot ($name + '.log'))
        $result = Get-Content (Join-Path $output 'result.json') -Raw | ConvertFrom-Json
        Write-Output "$name : $($result.passed) PASS / $($result.failed) FAIL"
    }
    & ./work/hd-world-pilot/tools/test.ps1 -OutputDirectory (Join-Path $reportRoot 'world-regression') *> (Join-Path $reportRoot 'world-regression.log')
    Write-Output 'World regression passed.'
    & ./work/hd-world-pilot/tools/test-menu.ps1 *> (Join-Path $reportRoot 'menu-regression.log')
    Copy-Item -LiteralPath build/hd-world-pilot/menu-regression -Destination (Join-Path $reportRoot 'menu-regression') -Recurse
    Write-Output 'Menu regression passed.'
}
if ((Get-FileHash -LiteralPath $buildExe).Hash -ne $hash) { throw 'Build EXE changed during validation.' }
