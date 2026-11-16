[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime = Join-Path $root 'runtime/hd-world-pilot/data/art/hd/player-male-vault13'
$output = Join-Path $root 'build/hd-player-male/fallback-v1'
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Close Fallout before testing.' }
if (Test-Path -LiteralPath $output) { throw 'Fallback output already exists; preserve its evidence.' }
New-Item -ItemType Directory -Path $output | Out-Null
$cases = @(
    @{ Name = 'missing-walk'; File = 'walk-d5-f007.rgba'; Count = 53; Missing = $true },
    @{ Name = 'corrupt-idle'; File = 'stand-d0.rgba'; Count = 53; Missing = $false },
    @{ Name = 'missing-registry'; File = 'registry.tsv'; Count = 0; Missing = $true }
)
$results = @()
foreach ($case in $cases) {
    $target = Join-Path $runtime $case.File
    $hold = Join-Path $output ($case.File + '.' + $case.Name + '.backup')
    $original = [IO.File]::ReadAllBytes($target)
    $originalHash = (Get-FileHash -LiteralPath $target).Hash
    try {
        if ($case.Missing) { Move-Item -LiteralPath $target -Destination $hold }
        else {
            [IO.File]::WriteAllBytes($hold, $original)
            [IO.File]::WriteAllBytes($target, [byte[]](70,49,72,68))
        }
        & (Join-Path $PSScriptRoot 'test-player.ps1') -OutputDirectory (Join-Path $output $case.Name) -ExpectedFrameCount $case.Count *> (Join-Path $output ($case.Name + '.log'))
    } finally {
        [IO.File]::WriteAllBytes($target, $original)
        if ((Get-FileHash -LiteralPath $target).Hash -ne $originalHash) { throw "Failed to restore $target" }
    }
    $results += [ordered]@{
        case = $case.Name
        file = $case.File
        restored_sha256 = $originalHash
        result = (Get-Content -LiteralPath (Join-Path $output ($case.Name + '/result.json')) -Raw | ConvertFrom-Json)
    }
}
[ordered]@{
    completed_utc = [DateTime]::UtcNow.ToString('o')
    executable_sha256 = (Get-FileHash -LiteralPath (Join-Path $root 'runtime/hd-world-pilot/fallout-ce.exe')).Hash
    all_files_restored = $true
    cases = $results
} | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
Write-Output 'All three player fallback cases passed; original runtime files restored.'
