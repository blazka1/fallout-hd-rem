[CmdletBinding()]
param(
    # All remains accepted for compatibility with the original build command.
    [ValidateSet('All', 'Fallout')]
    [string]$Component = 'Fallout',
    [ValidateRange(1, 32)]
    [int]$Jobs = 6
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path $PSScriptRoot -Parent
$falloutSource = Join-Path $projectRoot 'fallout1-ce-main'
$falloutBuild = Join-Path $projectRoot 'build/fallout1-ce'
$logRoot = Join-Path $projectRoot 'build/logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

function Invoke-LoggedNative {
    param([string]$Executable, [string[]]$NativeArguments, [string]$LogName)
    $logPath = Join-Path $logRoot $LogName
    Write-Output "Running $Executable $($NativeArguments -join ' ')"
    Write-Output "Log: $logPath"
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Executable @NativeArguments *> $logPath
        $nativeExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($nativeExit -ne 0) {
        Get-Content -LiteralPath $logPath -Tail 45 | Write-Output
        throw "$Executable failed with exit code $nativeExit. See $logPath"
    }
    Write-Output "Completed: $LogName"
}

$cmakeExe = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
if (-not (Test-Path -LiteralPath $cmakeExe)) {
    $cmakeExe = (Get-Command cmake -ErrorAction Stop).Source
}
Invoke-LoggedNative -Executable $cmakeExe -NativeArguments @(
    '-S', $falloutSource, '-B', $falloutBuild,
    '-G', 'Visual Studio 17 2022', '-A', 'x64', '-T', 'host=x64'
) -LogName 'fallout-configure.log'
Invoke-LoggedNative -Executable $cmakeExe -NativeArguments @(
    '--build', $falloutBuild, '--config', 'RelWithDebInfo',
    '--parallel', "$Jobs"
) -LogName 'fallout-build.log'
$falloutExe = Join-Path $falloutBuild 'RelWithDebInfo/fallout-ce.exe'
if (-not (Test-Path -LiteralPath $falloutExe)) { throw "Missing output: $falloutExe" }
Write-Output "Fallout executable: $falloutExe"
