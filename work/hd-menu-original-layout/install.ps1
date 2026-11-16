$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$runtime=Join-Path $root 'runtime/hd-world-pilot'
$backup=Join-Path $root 'build/backups/before-original-layout-menu-20261114'
$reportRoot=Join-Path $root 'build/hd-menu-original-layout'
$stage=Join-Path $reportRoot 'runtime-v3'
$checks=Get-Content (Join-Path $reportRoot 'preview-v3/manifest.json') -Raw | ConvertFrom-Json
$pixels=Get-Content (Join-Path $reportRoot 'pixel-check.json') -Raw | ConvertFrom-Json
$exe=Join-Path $runtime 'fallout-ce.exe'
$candidate=Join-Path $stage 'fallout-ce.exe'
if(Get-Process -Name fallout-ce -ErrorAction SilentlyContinue){throw 'Close Fallout before installing.'}
if($checks.failed -ne 0 -or $checks.passed -ne 139 -or -not $pixels.no_tint_or_darkening){throw 'Checks failed.'}
if((Get-FileHash $candidate).Hash -ne $checks.executable_sha256){throw 'Candidate changed after tests.'}
if((Get-FileHash $exe).Hash -ne (Get-FileHash (Join-Path $backup 'runtime/hd-world-pilot/fallout-ce.exe')).Hash){throw 'Runtime executable changed since backup.'}
$sourceHashes=Get-Content (Join-Path $root 'build/hd-world-pilot/logs/source-hashes.json') -Raw | ConvertFrom-Json
foreach($file in $sourceHashes){if((Get-FileHash (Join-Path $root ('work/hd-world-pilot/fallout1-ce-main/'+$file.path))).Hash -ne $file.sha256){throw 'Source changed since compilation.'}}
$protected=@(Get-ChildItem $runtime -Recurse -File | Where-Object {$_.FullName -ne $exe} | ForEach-Object {[ordered]@{path=$_.FullName;hash=(Get-FileHash $_.FullName).Hash}})
$newArt=Join-Path $runtime 'data/art/hd/main-menu/menu-background-v2.bmp'
if(Test-Path $newArt){throw 'Unexpected existing v2 background; inspect before replacing.'}
$selected=Join-Path $root 'assets/hd/main-menu/background-seed-qwen-v2'
New-Item -ItemType Directory -Force -Path $selected | Out-Null
Copy-Item (Join-Path $root 'assets/generated/main-menu/original-layout-20261114/background-4k.png') (Join-Path $selected 'background-4k.png')
Copy-Item (Join-Path $stage 'data/art/hd/main-menu/menu-background-v2.bmp') $newArt
Copy-Item $candidate $exe -Force
if((Get-FileHash $exe).Hash -ne $checks.executable_sha256){throw 'Installed hash mismatch.'}
foreach($file in $protected){if((Get-FileHash $file.path).Hash -ne $file.hash){throw "Protected file changed: $($file.path)"}}
$receipt=[ordered]@{
 status='installed-and-verified';completed_utc=[DateTime]::UtcNow.ToString('o');runtime='runtime/hd-world-pilot';
 executable_sha256=$checks.executable_sha256;background_sha256=(Get-FileHash $newArt).Hash;
 selected_png='assets/hd/main-menu/background-seed-qwen-v2/background-4k.png';
 png_sha256=(Get-FileHash (Join-Path $selected 'background-4k.png')).Hash;
 generation='assets/generated/main-menu/original-layout-20261114';
 source_portrait='assets/generated/main-menu/seed-qwen-20261114-v1/portrait-seed-qwen-1800x2160.png';
 layout='Intro, New Game, Load Game, Credits, Exit; upper-right compact block';
 removed='Title, subtitle, key hints, instructions, footer, decorative lines, grain, tint and dark fades';
 retained='Functional button names and current button artwork; all menu actions/hotkeys';
 checks=$checks;pixel_checks=$pixels;protected_runtime_files=$protected.Count;
 backup='build/backups/before-original-layout-menu-20261114';AGENTS_modified=$false;
 separate_classic_and_hd_menu_runtimes_modified=$false
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $reportRoot 'integration.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $selected 'manifest.json') -Encoding utf8
Write-Output "Installed: $($checks.executable_sha256); protected $($protected.Count) existing runtime files."
