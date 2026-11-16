[CmdletBinding()]
param([switch]$AssetsOnly)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$runtime = Join-Path $root 'runtime/hd-world-pilot'
$package = Join-Path $root 'assets/hd/player-male-vault13/v1-x4'
$destination = Join-Path $runtime 'data/art/hd/player-male-vault13'
$exe = Join-Path $root 'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
if (Get-Process -Name fallout-ce -ErrorAction SilentlyContinue) { throw 'Close Fallout before installing the test build.' }
$manifest = Get-Content -LiteralPath (Join-Path $package 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.image_count -ne 54 -or @($manifest.entries).Count -ne 54) { throw 'Incomplete actor package' }
if ((Get-FileHash -LiteralPath (Join-Path $package 'registry.tsv')).Hash -ne $manifest.registry_sha256) { throw 'Actor registry hash mismatch' }
foreach ($entry in $manifest.entries) {
    if ($entry.filename -notmatch '^[a-zA-Z0-9_-]+\.rgba$') { throw 'Unsafe asset name' }
    if ((Get-FileHash -LiteralPath (Join-Path $package $entry.filename)).Hash -ne $entry.rgba_sha256) { throw "Actor hash mismatch: $($entry.filename)" }
}
if (-not $AssetsOnly -and -not (Test-Path -LiteralPath $exe)) { throw 'Build isolated pilot first' }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
foreach ($name in @('registry.tsv','manifest.json') + @($manifest.entries | ForEach-Object { $_.filename })) {
    Copy-Item -LiteralPath (Join-Path $package $name) -Destination (Join-Path $destination $name) -Force
    if ((Get-FileHash -LiteralPath (Join-Path $package $name)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $destination $name)).Hash) { throw "Installed hash mismatch: $name" }
}
if (-not $AssetsOnly) { Copy-Item -LiteralPath $exe -Destination (Join-Path $runtime 'fallout-ce.exe') -Force }
# One component setting only; preserve all other runtime preferences and paths.
$config = Join-Path $runtime 'fallout.cfg'
$text = [IO.File]::ReadAllText($config)
if ($text -match '(?m)^hd_player_male=') { $text = [regex]::Replace($text, '(?m)^hd_player_male=[^\r\n]*', 'hd_player_male=1') }
elseif ($text -match '(?m)^\[remaster\]') { $text = [regex]::Replace($text, '(?m)^\[remaster\]\r?\n', "[remaster]`r`nhd_player_male=1`r`n") }
else { $text += "`r`n[remaster]`r`nhd_player_male=1`r`n" }
[IO.File]::WriteAllText($config, $text, [Text.Encoding]::ASCII)
Write-Output 'Installed 54 actor images into the world pilot; cave/menu assets and saves retained.'
