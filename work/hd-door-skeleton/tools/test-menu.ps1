[CmdletBinding()]
param([string]$ProjectRoot = (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent))

# Runs the existing 139 menu checks in the isolated pilot only.
# Neither scripts/test-hd-menu.ps1 nor the shared menu runtime/reports are changed.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$output = Join-Path $projectPath 'build/hd-door-skeleton/menu-regression-v18'
$executable = Join-Path $runtime 'fallout-ce.exe'
if (-not (Test-Path -LiteralPath $executable)) { throw "Missing pilot executable: $executable" }
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) {
    throw 'Close the running Fallout game before testing: the engine permits only one instance.'
}
foreach ($relative in @('src/game/hd_mainmenu.cc', 'src/game/hd_mainmenu.h')) {
    $original = Join-Path $projectPath "fallout1-ce-main/$relative"
    $isolated = Join-Path $projectPath "work/hd-world-pilot/fallout1-ce-main/$relative"
    if ((Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $isolated -Algorithm SHA256).Hash) {
        throw "The finished menu source differs in the pilot: $relative"
    }
}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$previousPreview = $env:FALLOUT_HD_MENU_PREVIEW
$previousExpect = $env:FALLOUT_HD_MENU_EXPECT_HD
$previousWorld = $env:FALLOUT_HD_WORLD_PREVIEW
try {
    $env:FALLOUT_HD_MENU_PREVIEW = $output
    $env:FALLOUT_HD_MENU_EXPECT_HD = '1'
    $env:FALLOUT_HD_WORLD_PREVIEW = $null
    $startedUtc = [DateTime]::UtcNow
    $process = Start-Process -FilePath $executable -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(45000)) {
        # This is only the hidden process created by this test, never an existing game.
        Stop-Process -Id $process.Id -Force
        throw 'Isolated HD menu preview exceeded 45 seconds.'
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "Isolated HD menu preview failed: $($process.ExitCode)" }
    $reportLines = @()
    foreach ($reportName in @('checks.txt', 'integration.txt')) {
        $reportFile = Get-Item -LiteralPath (Join-Path $output $reportName)
        if ($reportFile.LastWriteTimeUtc -lt $startedUtc) { throw "Stale menu regression report: $reportName" }
        $reportLines += @(Get-Content -LiteralPath $reportFile.FullName)
    }
    $passed = @($reportLines | Where-Object { $_ -match '^PASS ' }).Count
    $failed = @($reportLines | Where-Object { $_ -match '^FAIL ' }).Count
    [ordered]@{
        completed_utc = [DateTime]::UtcNow.ToString('o')
        runtime = $runtime
        executable_sha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
        original_menu_checks_expected = 139
        passed = $passed
        failed = $failed
        menu_sources_identical_to_original = $true
        output = $output
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    if ($passed -lt 139 -or $failed -ne 0) { throw "Menu regression: $passed PASS, $failed FAIL; expected at least 139 PASS and zero failures." }
    Write-Output "Isolated menu regression: $passed PASS, $failed FAIL. Reports: $output"
} finally {
    $env:FALLOUT_HD_MENU_PREVIEW = $previousPreview
    $env:FALLOUT_HD_MENU_EXPECT_HD = $previousExpect
    $env:FALLOUT_HD_WORLD_PREVIEW = $previousWorld
}
