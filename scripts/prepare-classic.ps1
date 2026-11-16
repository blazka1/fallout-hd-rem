[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$sourcePath = Join-Path $projectPath 'FALLOUT (extract.me)'
$runtimePath = Join-Path $projectPath 'runtime/classic'
$buildExe = Join-Path $projectPath 'build/fallout1-ce/RelWithDebInfo/fallout-ce.exe'
$masterPath = Join-Path $sourcePath 'MASTER.DAT'
$critterPath = Join-Path $sourcePath 'CRITTER.DAT'
$musicPath = Join-Path $sourcePath 'DATA/SOUND/MUSIC'
foreach ($required in @($buildExe, $masterPath, $critterPath, $musicPath)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing required path: $required" }
}

New-Item -ItemType Directory -Path (Join-Path $runtimePath 'data') -Force | Out-Null
$runtimeExe = Join-Path $runtimePath 'fallout-ce.exe'
if (Test-Path -LiteralPath $runtimeExe) {
    Write-Output 'Existing classic executable preserved.'
} else {
    Copy-Item -LiteralPath $buildExe -Destination $runtimeExe
}

$configPath = Join-Path $runtimePath 'fallout.cfg'
if (-not (Test-Path -LiteralPath $configPath)) {
    $musicDirectory = $musicPath.Replace('/', '\').TrimEnd('\') + '\'
    @"
[system]
master_dat=$masterPath
critter_dat=$critterPath
master_patches=data
critter_patches=data
language=english
art_cache_size=64

[sound]
music_path1=$musicDirectory
music_path2=$musicDirectory

[preferences]
subtitles=1
"@ | Set-Content -LiteralPath $configPath -Encoding ascii
}
$resolutionPath = Join-Path $runtimePath 'f1_res.ini'
if (-not (Test-Path -LiteralPath $resolutionPath)) {
    @'
[MAIN]
SCR_WIDTH=1280
SCR_HEIGHT=960
WINDOWED=1
SCALE_2X=1
'@ | Set-Content -LiteralPath $resolutionPath -Encoding ascii
}

$report = [ordered]@{
    created_at_utc = [DateTime]::UtcNow.ToString('o')
    runtime = $runtimePath
    executable_sha256 = (Get-FileHash -LiteralPath $runtimeExe -Algorithm SHA256).Hash.ToLowerInvariant()
    source_data = @(
        [ordered]@{path=$masterPath; bytes=(Get-Item -LiteralPath $masterPath).Length; sha256=(Get-FileHash -LiteralPath $masterPath -Algorithm SHA256).Hash.ToLowerInvariant()},
        [ordered]@{path=$critterPath; bytes=(Get-Item -LiteralPath $critterPath).Length; sha256=(Get-FileHash -LiteralPath $critterPath -Algorithm SHA256).Hash.ToLowerInvariant()}
    )
    source_edition = 'CD readme identifies Fallout 1.0, 29 September 1997; compatibility requires runtime verification'
    first_map = 'maps/v13ent.map'
    status = 'configured; gameplay verification tracked separately'
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $runtimePath 'setup-manifest.json') -Encoding utf8
Write-Output "Classic runtime ready: $runtimePath"
Write-Output 'Original DAT archives are referenced in place; local saves/patches use runtime/classic/data.'
