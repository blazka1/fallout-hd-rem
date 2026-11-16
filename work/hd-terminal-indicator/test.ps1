param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateSet('terminal','world','benchmark','hud','menu')][string]$Mode = 'terminal',
    [string]$CompanionPath = '',
    [string]$Executable = '',
    [int]$ExpectedLoaded = 1
)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$exe = Join-Path $runtime 'fallout-terminal-test.exe'
if ($Executable) { $exe = [IO.Path]::GetFullPath((Join-Path $root $Executable)) }
if (Get-Process -Name 'fallout-ce','fallout-terminal-test' -ErrorAction SilentlyContinue) { throw 'Close Fallout before this isolated test; no process was stopped.' }
$output = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (Test-Path -LiteralPath (Join-Path $output 'manifest.json')) { throw 'Use a new output directory.' }
New-Item -ItemType Directory -Force -Path $output | Out-Null
$names = @('FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_WORLD_EXPECT_COUNT','FALLOUT_HD_TERMINAL_ONLY','FALLOUT_HD_TERMINAL_EXPECT_LOADED','FALLOUT_HD_TERMINAL_LIT_ASSET','FALLOUT_HD_WORLD_BENCHMARK','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_HUD_EXPECT_LOADED','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_MENU_EXPECT_HD','FALLOUT_HD_PLAYER_PREVIEW')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process'); [Environment]::SetEnvironmentVariable($name,$null,'Process') }
$started = Get-Date
$configPath = Join-Path $runtime 'fallout.cfg'
$configBytes = [IO.File]::ReadAllBytes($configPath)
try {
    $env:FALLOUT_HD_WORLD_PREVIEW = $output
    $env:FALLOUT_HD_WORLD_EXPECT_COUNT = '206'
    if ($Mode -eq 'terminal') { $env:FALLOUT_HD_TERMINAL_ONLY = '1' }
    if ($Mode -eq 'benchmark') { $env:FALLOUT_HD_WORLD_BENCHMARK = $output }
    if ($Mode -eq 'hud') { $env:FALLOUT_HD_WORLD_PREVIEW = $null; $env:FALLOUT_HD_HUD_PREVIEW = $output; $env:FALLOUT_HD_HUD_EXPECT_LOADED = '1' }
    if ($Mode -eq 'menu') { $env:FALLOUT_HD_WORLD_PREVIEW = $null; $env:FALLOUT_HD_MENU_PREVIEW = $output; $env:FALLOUT_HD_MENU_EXPECT_HD = '1' }
    $env:FALLOUT_HD_TERMINAL_EXPECT_LOADED = [string]$ExpectedLoaded
    if ($CompanionPath) { $env:FALLOUT_HD_TERMINAL_LIT_ASSET = [IO.Path]::GetFullPath((Join-Path $root $CompanionPath)) }
    $process = Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(240000)) { Stop-Process -Id $process.Id -Force; throw 'Own test process exceeded 240 seconds.' }
    $process.Refresh()
    $resultPath = Join-Path $output 'result.json'
    if ($Mode -eq 'benchmark') { $resultPath = Join-Path $output 'benchmark.json' }
    if ($Mode -eq 'menu') {
        $lines = @(Get-Content -LiteralPath (Join-Path $output 'checks.txt')) + @(Get-Content -LiteralPath (Join-Path $output 'integration.txt'))
        @{passed=@($lines | Where-Object { $_ -match '^PASS ' }).Count; failed=@($lines | Where-Object { $_ -match '^FAIL ' }).Count} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding utf8
    }
    if (-not (Test-Path -LiteralPath $resultPath) -or (Get-Item -LiteralPath $resultPath).LastWriteTime -lt $started) { throw 'Missing/stale result.' }
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    Add-Type -AssemblyName System.Drawing
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $image = [Drawing.Image]::FromFile($bmp.FullName)
        try { $image.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png) } finally { $image.Dispose() }
    }
    [ordered]@{ created=[DateTime]::UtcNow.ToString('o'); executable_sha256=(Get-FileHash -LiteralPath $exe).Hash; exit_code=$process.ExitCode; mode=$Mode; expected_loaded=$ExpectedLoaded; companion_override=$CompanionPath; result=$result; base_sha256=(Get-FileHash -LiteralPath (Join-Path $runtime 'data/art/hd/world-pilot/asset-010.rgba')).Hash; companion_sha256=(Get-FileHash -LiteralPath (Join-Path $runtime 'data/art/hd/world-pilot/terminal-indicator-on.rgba')).Hash } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $output 'checks.txt') | Select-Object -Last 5
    if ($process.ExitCode -ne 0 -or $result.failed -ne 0) { throw "Failed test; inspect $output" }
} finally {
    [IO.File]::WriteAllBytes($configPath,$configBytes)
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
