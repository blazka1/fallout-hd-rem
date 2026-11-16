[CmdletBinding()]
param(
    [ValidateSet('combat','world','viewport','hud','menu','benchmark')][string]$Mode = 'combat',
    [int]$Width = 1920,
    [int]$Height = 1080,
    [ValidateSet(0,1)][int]$Scale2x = 1,
    [ValidateSet(0,1)][int]$FullHeight = 1,
    [string]$OutputDirectory,
    [string]$Executable = '',
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
if (Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue) {
    throw 'Close Fallout before testing; its named mutex permits one instance. No process was stopped.'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { throw 'Choose a fresh output directory.' }
$output = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if (Test-Path -LiteralPath (Join-Path $output 'checks.txt')) { throw 'Existing results must not be overwritten.' }
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$stage = Join-Path $root 'build/combat-crash-fix/test-runtime'
New-Item -ItemType Directory -Force -Path $stage,$output | Out-Null
if ([string]::IsNullOrWhiteSpace($Executable)) {
    $Executable = Join-Path $root 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
}
$exe = Join-Path $stage 'fallout-ce.exe'
Copy-Item -LiteralPath $Executable -Destination $exe
$stageArt = Join-Path $stage 'data/art'
if (-not (Test-Path -LiteralPath $stageArt)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $stageArt -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $runtime 'data/art') -Destination $stageArt -Recurse
}
$config = Get-Content -LiteralPath (Join-Path $runtime 'fallout.cfg') -Raw
$config = $config -replace '(?m)^borderless=.*$', 'borderless=0'
$config = $config -replace '(?m)^full_height_world=.*\r?\n', ''
$config = $config -replace '\[remaster\]', "[remaster]`r`nfull_height_world=$FullHeight"
Set-Content -LiteralPath (Join-Path $stage 'fallout.cfg') -Value $config -Encoding ascii
Set-Content -LiteralPath (Join-Path $stage 'f1_res.ini') -Encoding ascii -Value @"
[MAIN]
SCALE_2X=$Scale2x
WINDOWED=1
SCR_WIDTH=$Width
SCR_HEIGHT=$Height
"@
$variables = @('FALLOUT_COMBAT_TEST','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_VIEWPORT_ONLY','FALLOUT_HD_WORLD_EXPECT_COUNT',
    'FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_HUD_EXPECT_LOADED','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_MENU_EXPECT_HD',
    'FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_WORLD_BENCHMARK')
$previous = @{}
foreach ($name in $variables) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
    [Environment]::SetEnvironmentVariable($name,$null,'Process')
}
try {
    if ($Mode -eq 'combat') { $env:FALLOUT_COMBAT_TEST='1' }
    switch ($Mode) {
        'hud' { $env:FALLOUT_HD_HUD_PREVIEW=$output; $env:FALLOUT_HD_HUD_EXPECT_LOADED='1' }
        'menu' { $env:FALLOUT_HD_MENU_PREVIEW=$output; $env:FALLOUT_HD_MENU_EXPECT_HD='1' }
        default {
            $env:FALLOUT_HD_WORLD_PREVIEW=$output
            $env:FALLOUT_HD_WORLD_EXPECT_COUNT=[string](Get-Content -LiteralPath (Join-Path $stageArt 'hd/world-pilot/manifest.json') -Raw | ConvertFrom-Json).asset_count
            if ($Mode -eq 'viewport') { $env:FALLOUT_HD_VIEWPORT_ONLY='1' }
            if ($Mode -eq 'benchmark') { $env:FALLOUT_HD_WORLD_BENCHMARK=$output }
        }
    }
    $process = Start-Process -FilePath $exe -WorkingDirectory $stage -WindowStyle Hidden -PassThru
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not $process.WaitForExit(1000)) {
        if ($timer.Elapsed.TotalSeconds -gt 180) {
            Stop-Process -Id $process.Id -Force
            throw 'Own isolated test process exceeded 180 seconds.'
        }
    }
    $process.Refresh()
    Add-Type -AssemblyName System.Drawing
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $picture = [Drawing.Image]::FromFile($bmp.FullName)
        try { $picture.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png) }
        finally { $picture.Dispose() }
    }
    $lines = @()
    if (Test-Path -LiteralPath (Join-Path $output 'checks.txt')) {
        $lines = @(Get-Content -LiteralPath (Join-Path $output 'checks.txt'))
    }
    if (Test-Path -LiteralPath (Join-Path $output 'integration.txt')) {
        $lines += @(Get-Content -LiteralPath (Join-Path $output 'integration.txt'))
    }
    $passed = @($lines | Where-Object { $_ -match '^PASS ' }).Count
    $failed = @($lines | Where-Object { $_ -match '^FAIL ' }).Count
    [ordered]@{
        created_utc=[DateTime]::UtcNow.ToString('o'); mode=$Mode; width=$Width; height=$Height;
        scale_2x=$Scale2x; full_height=$FullHeight; executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;
        source_executable=$Executable; stage=$stage; passed=$passed; failed=$failed; exit_code=$process.ExitCode
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
    $lines | Where-Object { $_ -match '^FAIL |^TOTAL ' } | Write-Output
    Write-Output "$Mode : $passed PASS / $failed FAIL. $output"
    if ($process.ExitCode -ne 0 -or $failed -ne 0 -or $passed -eq 0) { throw "Test failed, exit $($process.ExitCode)" }
} finally {
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}

