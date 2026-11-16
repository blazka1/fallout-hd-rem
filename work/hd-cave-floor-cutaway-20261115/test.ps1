param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateSet('world','smoke','terminal','menu','hud','diagnostic')][string]$Mode='world',
    [int]$ExpectedTileVariants=-1,
    [string]$RuntimeDirectory='runtime/hd-world-pilot',
    [string]$Executable='runtime/hd-world-pilot/fallout-floor-test.exe'
)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtime=[IO.Path]::GetFullPath((Join-Path $root $RuntimeDirectory))
$exe=[IO.Path]::GetFullPath((Join-Path $root $Executable))
if(Get-Process -Name 'fallout-ce','fallout-floor-test','fallout-seam-test','fallout-terminal-test' -ErrorAction SilentlyContinue){throw 'Close the game before running the render tests.'}
$output=[IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
if(Test-Path -LiteralPath (Join-Path $output 'manifest.json')){throw 'Use a fresh output directory.'}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$names=@('FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_WORLD_EXPECT_COUNT','FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_MENU_EXPECT_HD','FALLOUT_HD_TILE_EXPECT_COUNT','FALLOUT_HD_TILE_VARIANT_SMOKE','FALLOUT_HD_SEAM_DIAGNOSTIC','FALLOUT_HD_TERMINAL_ONLY','FALLOUT_HD_TERMINAL_EXPECT_LOADED','FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_HUD_EXPECT_LOADED')
$previous=@{}
foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$null,'Process')}
$cfg=Join-Path $runtime 'fallout.cfg';$cfgBytes=[IO.File]::ReadAllBytes($cfg)
$automap=Join-Path $runtime 'data/MAPS/AUTOMAP.DB'
$automapBytes=if(Test-Path -LiteralPath $automap){[IO.File]::ReadAllBytes($automap)}else{$null}
$started=Get-Date
try{
 $env:FALLOUT_HD_WORLD_PREVIEW=$output
 $env:FALLOUT_HD_WORLD_EXPECT_COUNT=[string]((Get-Content -LiteralPath (Join-Path $runtime 'data/art/hd/world-pilot/manifest.json') -Raw | ConvertFrom-Json).asset_count)
 if($ExpectedTileVariants -ge 0){$env:FALLOUT_HD_TILE_EXPECT_COUNT=[string]$ExpectedTileVariants}
 if($Mode -eq 'smoke'){$env:FALLOUT_HD_TILE_VARIANT_SMOKE='1'}
 if($Mode -eq 'diagnostic'){$env:FALLOUT_HD_SEAM_DIAGNOSTIC='1'}
 if($Mode -eq 'terminal'){$env:FALLOUT_HD_TERMINAL_ONLY='1';$env:FALLOUT_HD_TERMINAL_EXPECT_LOADED='1'}
 if($Mode -eq 'menu'){$env:FALLOUT_HD_WORLD_PREVIEW=$null;$env:FALLOUT_HD_MENU_PREVIEW=$output;$env:FALLOUT_HD_MENU_EXPECT_HD='1'}
 if($Mode -eq 'hud'){$env:FALLOUT_HD_WORLD_PREVIEW=$null;$env:FALLOUT_HD_HUD_PREVIEW=$output;$env:FALLOUT_HD_HUD_EXPECT_LOADED='1'}
 $proc=Start-Process -FilePath $exe -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
 $timer=[Diagnostics.Stopwatch]::StartNew()
 while(-not $proc.WaitForExit(1000)){
  if($timer.Elapsed.TotalSeconds -gt 240){Stop-Process -Id $proc.Id -Force;throw 'Own test process timed out.'}
 }
 $proc.Refresh()
 if($Mode -eq 'menu'){
  $lines=@(Get-Content -LiteralPath (Join-Path $output 'checks.txt'))+@(Get-Content -LiteralPath (Join-Path $output 'integration.txt'))
  @{passed=@($lines|Where-Object{$_ -match '^PASS '}).Count;failed=@($lines|Where-Object{$_ -match '^FAIL '}).Count}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $output 'result.json') -Encoding utf8
 }
 $resultFile=Join-Path $output 'result.json'
 if(-not(Test-Path -LiteralPath $resultFile) -or (Get-Item -LiteralPath $resultFile).LastWriteTime -lt $started){throw 'Missing or stale test result.'}
 $result=Get-Content -LiteralPath $resultFile -Raw|ConvertFrom-Json
 Add-Type -AssemblyName System.Drawing
 foreach($bmp in Get-ChildItem -LiteralPath $output -Filter '*.bmp' -File){
  $im=[Drawing.Image]::FromFile($bmp.FullName)
  try{$im.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png)}finally{$im.Dispose()}
 }
 [ordered]@{created=[DateTime]::UtcNow.ToString('o');executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;exit_code=$proc.ExitCode;mode=$Mode;expected_tile_variants=$ExpectedTileVariants;runtime=$runtime;result=$result}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding utf8
 Get-Content -LiteralPath (Join-Path $output 'checks.txt')|Select-Object -Last 4
 if($proc.ExitCode -ne 0 -or $result.failed -ne 0){throw "Render test failed: $output"}
}finally{
 [IO.File]::WriteAllBytes($cfg,$cfgBytes)
 if($null -ne $automapBytes){[IO.File]::WriteAllBytes($automap,$automapBytes)}elseif(Test-Path -LiteralPath $automap){Remove-Item -LiteralPath $automap}
 foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}
}
