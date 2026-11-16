[CmdletBinding()]
param(
    [ValidateRange(1, 32)][int]$Jobs = 6,
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$sourcePath = Join-Path $projectPath 'work/hd-wall-original-restore-20261116/test-source'
$buildPath = Join-Path $projectPath 'build/hd-wall-original-restore-20261116/test-msvc'
$logPath = Join-Path $projectPath 'build/hd-wall-original-restore-20261116/test-build-logs'
$existingDeps = Join-Path $projectPath 'build/fallout1-ce/_deps'
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath 'CMakeLists.txt'))) {
    throw "Missing isolated source copy: $sourcePath"
}
New-Item -ItemType Directory -Force -Path $buildPath, $logPath | Out-Null

# Use the already downloaded sources, but compile all dependency objects in this build.
# FULLY_DISCONNECTED ensures this experiment never updates or downloads dependencies.
$configureArguments = @('-S', $sourcePath, '-B', $buildPath,
    '-G', 'Visual Studio 17 2022', '-A', 'x64', '-T', 'host=x64',
    '-DFETCHCONTENT_FULLY_DISCONNECTED=ON', '-DFETCHCONTENT_UPDATES_DISCONNECTED=ON')
foreach ($dependency in @('sdl2', 'adecode', 'fpattern')) {
    $dependencySource = Join-Path $existingDeps "$dependency-src"
    if (-not (Test-Path -LiteralPath (Join-Path $dependencySource 'CMakeLists.txt'))) {
        throw "Existing dependency source not found: $dependencySource. No download was attempted."
    }
    $configureArguments += "-DFETCHCONTENT_SOURCE_DIR_$($dependency.ToUpperInvariant())=$dependencySource"
}
$cmakeExe = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
if (-not (Test-Path -LiteralPath $cmakeExe)) { $cmakeExe = (Get-Command cmake -ErrorAction Stop).Source }

function Invoke-LoggedNative {
    param([string[]]$NativeArguments, [string]$LogName)
    $nativeLog = Join-Path $logPath $LogName
    Write-Output "CMake log: $nativeLog"
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $cmakeExe @NativeArguments *> $nativeLog
        $nativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($nativeExit -ne 0) {
        Get-Content -LiteralPath $nativeLog -Tail 45 | Write-Output
        throw "CMake failed with exit code $nativeExit. See $nativeLog"
    }
}

$sourceHashes = @(Get-ChildItem -LiteralPath $sourcePath -Recurse -File | Sort-Object FullName | ForEach-Object {
    [ordered]@{
        path = $_.FullName.Substring($sourcePath.Length + 1).Replace('\', '/')
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
})
$sourceHashes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $logPath 'source-hashes.json') -Encoding utf8
Invoke-LoggedNative -NativeArguments $configureArguments -LogName 'configure.log'
# Configuration names alone do not prove that MSVC optimization is enabled.
[xml]$generatedProject = Get-Content -LiteralPath (Join-Path $buildPath 'fallout-ce.vcxproj') -Raw
$releaseGroup = @($generatedProject.Project.ItemDefinitionGroup | Where-Object {
    $_.Condition -like '*RelWithDebInfo|x64*'
})
if ($releaseGroup.Count -ne 1 -or $releaseGroup[0].ClCompile.Optimization -ne 'MaxSpeed' -or
    $releaseGroup[0].ClCompile.PreprocessorDefinitions -notmatch '(^|;)NDEBUG(;|$)') {
    throw 'The isolated RelWithDebInfo target must use MSVC /O2 and NDEBUG. Check generated compilation options.'
}
Invoke-LoggedNative -NativeArguments @('--build', $buildPath, '--config', 'RelWithDebInfo', '--parallel', "$Jobs") -LogName 'build.log'
$executable = Join-Path $buildPath 'RelWithDebInfo/fallout-ce.exe'
if (-not (Test-Path -LiteralPath $executable)) { throw "Missing output: $executable" }
# Agents can work concurrently: do not publish a manifest for a changing source tree.
$changedDuringBuild = @($sourceHashes | Where-Object {
    $capturedPath = Join-Path $sourcePath $_.path
    -not (Test-Path -LiteralPath $capturedPath) -or
        (Get-FileHash -LiteralPath $capturedPath -Algorithm SHA256).Hash -ne $_.sha256
})
if ($changedDuringBuild.Count) {
    throw ('Source changed during compilation; rebuild after edits finish: ' + (($changedDuringBuild | ForEach-Object { $_.path }) -join ', '))
}
[ordered]@{
    built_utc = [DateTime]::UtcNow.ToString('o')
    source = $sourcePath
    build = $buildPath
    configuration = 'RelWithDebInfo'
    compiler_optimization = '/O2'
    ndebug_verified = $true
    dependencies_source = $existingDeps
    dependencies_downloads_disabled = $true
    source_files_verified_after_build = $sourceHashes.Count
    executable = $executable
    executable_sha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $logPath 'build-manifest.json') -Encoding utf8
Write-Output "Isolated pilot executable: $executable"
