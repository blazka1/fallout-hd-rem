[CmdletBinding()]
param([string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-menu'
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) { throw 'Close Fallout before running menu checks; the game uses a single-instance mutex.' }
$output = Join-Path $projectPath ('build/hd-menu-preview/runs/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $output -Force | Out-Null
$previous = $env:FALLOUT_HD_MENU_PREVIEW
$previousExpect = $env:FALLOUT_HD_MENU_EXPECT_HD
$retentionOutcome = 'Failed'
try {
    $env:FALLOUT_HD_MENU_PREVIEW = $output
    $env:FALLOUT_HD_MENU_EXPECT_HD = '1'
    $process = Start-Process -FilePath (Join-Path $runtime 'fallout-ce.exe') -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(45000)) {
        Stop-Process -Id $process.Id -Force
        throw 'HD menu preview exceeded 45 seconds.'
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "HD menu preview failed: $($process.ExitCode)" }
    Get-Content -LiteralPath (Join-Path $output 'checks.txt')
    Get-Content -LiteralPath (Join-Path $output 'integration.txt')
    $retentionOutcome = 'Passed'
} finally {
    $env:FALLOUT_HD_MENU_PREVIEW = $previous
    $env:FALLOUT_HD_MENU_EXPECT_HD = $previousExpect
    try {
        & (Join-Path $projectPath 'scripts/complete-build-check.ps1') -ProjectRoot $projectPath -RunDirectory $output -Component 'main-menu' -Outcome $retentionOutcome
    } catch { if ($retentionOutcome -eq 'Passed') { throw }; Write-Warning "Failed-run captures preserved: $_" }
}
