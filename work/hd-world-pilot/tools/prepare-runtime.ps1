[CmdletBinding()]
param(
    [switch]$AssetsOnly,
    [string]$ProjectRoot = (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent),
    [string]$AssetPackage = 'assets/hd/v13ent/v14-campfire-x4'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtime = Join-Path $projectPath 'runtime/hd-world-pilot'
$menuRuntime = Join-Path $projectPath 'runtime/hd-menu'
$gameData = Join-Path $projectPath 'FALLOUT (extract.me)'
$executable = Join-Path $projectPath 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
$assetPackagePath = if ([IO.Path]::IsPathRooted($AssetPackage)) {
    [IO.Path]::GetFullPath($AssetPackage)
} else {
    [IO.Path]::GetFullPath((Join-Path $projectPath $AssetPackage))
}
$reportDirectory = Join-Path $projectPath 'build/hd-world-pilot'
$python = 'C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe'
foreach ($required in @($python, (Join-Path $menuRuntime 'fallout.cfg'),
    (Join-Path $gameData 'MASTER.DAT'), (Join-Path $gameData 'CRITTER.DAT'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing: $required" }
}
if (-not $AssetsOnly -and -not (Test-Path -LiteralPath $executable)) {
    throw "Build the isolated pilot first: $executable"
}
$targetExe = Join-Path $runtime 'fallout-ce.exe'
$runningPilot = Get-Process -Name fallout-ce -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $targetExe }
if ($runningPilot) { throw 'The pilot game is running. Close that game before updating its textures or executable.' }

# The exporter validates ALL selected PNGs and original alpha masks before
# its first runtime write. Keep this before menu/configuration/runtime mutations.
# This is lossless decoding/packaging; it does not generate or resize artwork.
$selectedManifestPath = Join-Path $assetPackagePath 'manifest.json'
$selectedManifest = Get-Content -LiteralPath $selectedManifestPath -Raw | ConvertFrom-Json
$expectedAssetCount = [int]$selectedManifest.asset_count
$exporter = switch ($expectedAssetCount) {
    159 { 'export-runtime-assets.py' }
    174 { 'export-vault-runtime-assets.py' }
    default { throw "Unsupported selected package image count: $expectedAssetCount" }
}
& $python (Join-Path $PSScriptRoot $exporter) --source $assetPackagePath --runtime $runtime
if ($LASTEXITCODE -ne 0) { throw "World asset validation/packaging failed with exit code $LASTEXITCODE; preparation stopped." }
if ($selectedManifest.PSObject.Properties.Name -contains 'total_image_count') {
    $expectedAssetCount = [int]$selectedManifest.total_image_count
}
if ($exporter -eq 'export-runtime-assets.py') {
    [IO.File]::WriteAllText((Join-Path $runtime 'data/art/hd/world-pilot/variants.tsv'), "# no wall variants`n", [Text.Encoding]::ASCII)
    foreach ($sidecar in @('decor.tsv', 'decor-placements.tsv')) {
        [IO.File]::WriteAllText((Join-Path $runtime ('data/art/hd/world-pilot/' + $sidecar)), "# no decorations`n", [Text.Encoding]::ASCII)
    }
}
$worldManifestPath = Join-Path $runtime 'data/art/hd/world-pilot/manifest.json'
$worldManifest = Get-Content -LiteralPath $worldManifestPath -Raw | ConvertFrom-Json
if ($worldManifest.asset_count -ne $expectedAssetCount) { throw 'World package manifest does not contain the complete selected image inventory.' }
New-Item -ItemType Directory -Force -Path $runtime, $reportDirectory | Out-Null

# Copy only the finished menu's art. Do not copy another runtime's saves or automap.
# No game maps, object prototypes, or original DAT files are replaced by this pilot.
$menuFiles = @('data/art/hd/main-menu/menu-portrait-v1.bmp',
    'data/art/hd/main-menu/new-game/normal.bmp',
    'data/art/hd/main-menu/new-game/hover.bmp',
    'data/art/hd/main-menu/new-game/pressed.bmp')
$menuHashes = @()
foreach ($relativePath in $menuFiles) {
    $source = Join-Path $menuRuntime $relativePath
    $destination = Join-Path $runtime $relativePath
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing finished menu asset: $source" }
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) { throw "Menu copy hash mismatch: $relativePath" }
    $menuHashes += [ordered]@{ path = $relativePath; sha256 = $destinationHash; identical_to_menu_runtime = $true }
}

function Set-IniValue {
    param([string]$Text, [string]$Section, [string]$Key, [string]$Value)
    $sectionPattern = '(?ms)^\[' + [regex]::Escape($Section) + '\][^\r\n]*\r?\n(?<body>.*?)(?=^\[|\z)'
    $sectionMatch = [regex]::Match($Text, $sectionPattern)
    if (-not $sectionMatch.Success) { return $Text.TrimEnd() + "`r`n`r`n[$Section]`r`n$Key=$Value`r`n" }
    $body = $sectionMatch.Groups['body'].Value
    $keyPattern = '(?m)^' + [regex]::Escape($Key) + '=[^\r\n]*'
    if ([regex]::IsMatch($body, $keyPattern)) {
        $body = [regex]::Replace($body, $keyPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) "$Key=$Value" })
    } else { $body = "$Key=$Value`r`n" + $body }
    $replacement = "[$Section]`r`n" + $body
    return $Text.Substring(0, $sectionMatch.Index) + $replacement + $Text.Substring($sectionMatch.Index + $sectionMatch.Length)
}

$configPath = Join-Path $runtime 'fallout.cfg'
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $menuRuntime 'fallout.cfg') -Destination $configPath
}
$configText = [IO.File]::ReadAllText($configPath)
foreach ($setting in @(
    @('system', 'master_dat', (Join-Path $gameData 'MASTER.DAT')),
    @('system', 'critter_dat', (Join-Path $gameData 'CRITTER.DAT')),
    @('system', 'master_patches', 'data'), @('system', 'critter_patches', 'data'),
    @('remaster', 'borderless', '0'), @('remaster', 'hd_world_pilot', '1'))) {
    $configText = Set-IniValue -Text $configText -Section $setting[0] -Key $setting[1] -Value $setting[2]
}
[IO.File]::WriteAllText($configPath, $configText, [Text.Encoding]::ASCII)
$resolutionPath = Join-Path $runtime 'f1_res.ini'
$resolutionText = if (Test-Path -LiteralPath $resolutionPath) { [IO.File]::ReadAllText($resolutionPath) } else { "[MAIN]`r`n" }
foreach ($setting in @(@('SCR_WIDTH', '1920'), @('SCR_HEIGHT', '1080'), @('WINDOWED', '1'), @('SCALE_2X', '1'))) {
    $resolutionText = Set-IniValue -Text $resolutionText -Section 'MAIN' -Key $setting[0] -Value $setting[1]
}
[IO.File]::WriteAllText($resolutionPath, $resolutionText, [Text.Encoding]::ASCII)

if (-not $AssetsOnly) { Copy-Item -LiteralPath $executable -Destination (Join-Path $runtime 'fallout-ce.exe') -Force }
$runtimeExe = Join-Path $runtime 'fallout-ce.exe'
$runtimeHash = if (Test-Path -LiteralPath $runtimeExe) { (Get-FileHash -LiteralPath $runtimeExe -Algorithm SHA256).Hash } else { $null }
[ordered]@{
    prepared_utc = [DateTime]::UtcNow.ToString('o')
    runtime = $runtime
    assets_only = [bool]$AssetsOnly
    executable_sha256 = $runtimeHash
    menu_assets = $menuHashes
    menu_source_config_sha256 = (Get-FileHash -LiteralPath (Join-Path $menuRuntime 'fallout.cfg') -Algorithm SHA256).Hash
    isolated_configs_and_saves = $true
    copied_savegames = $false
    modified_maps_or_prototypes = $false
    logical_size = @(960, 540)
    window_size = @(1920, 1080)
    selected_package = $assetPackagePath
    asset_count = $worldManifest.asset_count
    registry_sha256 = $worldManifest.registry_sha256
    selected_assets = @($worldManifest.assets | Where-Object { $_.PSObject.Properties.Name -contains 'original_resource' } | ForEach-Object { $_.original_resource })
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $reportDirectory 'runtime-manifest.json') -Encoding utf8
Write-Output "Pilot runtime prepared: $runtime"
if ($AssetsOnly) { Write-Output 'Assets/configuration only; no executable was copied.' }
