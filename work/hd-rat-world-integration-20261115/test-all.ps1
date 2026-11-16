$ErrorActionPreference='Stop'
foreach($mode in @('player','rat','world','menu','hud')) {
    $output="build/hd-rat-world-integration-20261115/verified/$mode"
    $log="build/hd-rat-world-integration-20261115/logs/verified-$mode.log"
    & (Join-Path $PSScriptRoot 'test.ps1') -Mode $mode -OutputDirectory $output *> $log
    Write-Output "$mode complete"
}
foreach($case in @('missing-frame','corrupt-frame','missing-aimed','corrupt-aimed')) {
    & (Join-Path $PSScriptRoot 'test-fallback.ps1') -Case $case *> "build/hd-rat-world-integration-20261115/logs/verified-$case.log"
    Write-Output "$case complete"
}
