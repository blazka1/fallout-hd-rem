[CmdletBinding()]
param([string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent), [string]$OutputDirectory = 'build/hd-rat-20261115/menu-verified')
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-rat-pilot'
$output = Join-Path $projectPath $OutputDirectory
if (Get-Process -Name 'fallout-ce' -ErrorAction SilentlyContinue) { throw 'Another Fallout instance is running; preserved.' }
New-Item -ItemType Directory -Path $output -Force | Out-Null
$previous = $env:FALLOUT_HD_MENU_PREVIEW
$previousExpect = $env:FALLOUT_HD_MENU_EXPECT_HD
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
} finally {
    $env:FALLOUT_HD_MENU_PREVIEW = $previous
    $env:FALLOUT_HD_MENU_EXPECT_HD = $previousExpect
}
