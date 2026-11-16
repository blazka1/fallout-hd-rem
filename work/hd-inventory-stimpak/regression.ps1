$ErrorActionPreference = 'Stop'
foreach ($pidValue in @(4,8,21,29,30)) {
    & "$PSScriptRoot/test.ps1" -ItemPid $pidValue -OutputDirectory "build/hd-inventory-stimpak/preview/item-$pidValue" *> "build/hd-inventory-stimpak/item-$pidValue.log"
    $r = Get-Content "build/hd-inventory-stimpak/preview/item-$pidValue/result.json" -Raw | ConvertFrom-Json
    Write-Output "PID $pidValue : $($r.passed) PASS / $($r.failed) FAIL"
}
& ./work/hd-world-pilot/tools/test.ps1 -OutputDirectory build/hd-inventory-stimpak/world-regression *> build/hd-inventory-stimpak/world.log
Write-Output 'World passed'
& ./work/hd-world-pilot/tools/test-menu.ps1 *> build/hd-inventory-stimpak/menu.log
Copy-Item build/hd-world-pilot/menu-regression build/hd-inventory-stimpak/menu-regression -Recurse
Write-Output 'Menu passed'
