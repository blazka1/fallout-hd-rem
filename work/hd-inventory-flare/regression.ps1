$ErrorActionPreference='Stop'
foreach ($pidValue in @(79,4,8,21,29,30,40)) {
    & "$PSScriptRoot/test.ps1" -ItemPid $pidValue -OutputDirectory "build/hd-inventory-flare/preview/installed-$pidValue" *> "build/hd-inventory-flare/installed-$pidValue.log"
    $r=Get-Content "build/hd-inventory-flare/preview/installed-$pidValue/result.json" -Raw | ConvertFrom-Json
    Write-Output "PID $pidValue : $($r.passed) PASS / $($r.failed) FAIL"
}
& ./work/hd-world-pilot/tools/test.ps1 -OutputDirectory build/hd-inventory-flare/world-regression *> build/hd-inventory-flare/world.log
Write-Output 'World passed'
& ./work/hd-world-pilot/tools/test-menu.ps1 *> build/hd-inventory-flare/menu.log
Copy-Item build/hd-world-pilot/menu-regression build/hd-inventory-flare/menu-regression -Recurse
Write-Output 'Menu passed'
