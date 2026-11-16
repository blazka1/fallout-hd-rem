$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $root 'build/hd-menu-original-layout/preview-v3'
$stage = Join-Path $root 'build/hd-menu-original-layout/runtime-v3'
$live = Join-Path $root 'runtime/hd-world-pilot'
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Close Fallout before rendering the menu preview.' }
if (Test-Path $output) { throw 'Preview already exists; choose a new revision.' }
New-Item -ItemType Directory -Force -Path $output,$stage,(Join-Path $stage 'data/art/hd') | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe') -Destination $stage
Copy-Item -LiteralPath (Join-Path $live 'fallout.cfg') -Destination $stage
Copy-Item -LiteralPath (Join-Path $live 'f1_res.ini') -Destination $stage
Copy-Item -LiteralPath (Join-Path $live 'data/art/hd/main-menu') -Destination (Join-Path $stage 'data/art/hd/main-menu') -Recurse
Add-Type -AssemblyName System.Drawing
$portrait = Join-Path $root 'assets/generated/main-menu/original-layout-20261114/background-4k.png'
$im = [Drawing.Image]::FromFile($portrait)
try { $im.Save((Join-Path $stage 'data/art/hd/main-menu/menu-background-v2.bmp'),[Drawing.Imaging.ImageFormat]::Bmp) }
finally { $im.Dispose() }
$saved = @{}
$names = @('FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_MENU_EXPECT_HD','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_PLAYER_DEMO')
foreach ($name in $names) { $saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$null,'Process') }
try {
    $env:FALLOUT_HD_MENU_PREVIEW=$output
    $env:FALLOUT_HD_MENU_EXPECT_HD='1'
    $process=Start-Process -FilePath (Join-Path $stage 'fallout-ce.exe') -WorkingDirectory $stage -ArgumentList '[remaster]borderless=0' -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(45000)) { Stop-Process -Id $process.Id -Force;throw 'Own preview process timed out.' }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "Preview failed: $($process.ExitCode)" }
    foreach ($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File) {
        $pic=[Drawing.Image]::FromFile($bmp.FullName)
        try { $pic.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png) }
        finally { $pic.Dispose() }
    }
    $lines=@(Get-Content (Join-Path $output 'checks.txt'))+@(Get-Content (Join-Path $output 'integration.txt'))
    $passed=@($lines | Where-Object {$_ -match '^PASS '}).Count
    $failed=@($lines | Where-Object {$_ -match '^FAIL '}).Count
    [ordered]@{status='isolated-preview';passed=$passed;failed=$failed;live_runtime_modified=$false;portrait=$portrait;portrait_sha256=(Get-FileHash $portrait).Hash;executable_sha256=(Get-FileHash (Join-Path $stage 'fallout-ce.exe')).Hash;output=$output} | ConvertTo-Json | Set-Content (Join-Path $output 'manifest.json') -Encoding utf8
    if($failed -ne 0) { throw 'Preview checks failed.' }
    Write-Output "$passed PASS, $failed FAIL; $output"
} finally { foreach($name in $names) { [Environment]::SetEnvironmentVariable($name,$saved[$name],'Process') } }

