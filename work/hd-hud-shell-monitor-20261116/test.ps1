param([ValidateSet('hud','menu')][string]$Mode='hud',[string]$Name='candidate',[string]$Executable='',
    [ValidateSet('0','1')][string]$ExpectedPanel='1',[string]$PanelAsset='',[switch]$SkipPng)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$stage=Join-Path $PSScriptRoot 'runtime'
$out=Join-Path $root ('build/hd-hud-shell-install-20261116/'+$Name)
New-Item -ItemType Directory -Force -Path $out | Out-Null
if(Get-Process -Name fallout-ce -ErrorAction SilentlyContinue){throw 'Fallout is running; no process was stopped.'}
if(!$Executable){$Executable=Join-Path $stage 'fallout-ce.exe'}
elseif((Split-Path ([IO.Path]::GetFullPath($Executable)) -Parent) -ne $stage){
    # CE resolves fallout.cfg relative to argv[0], not the working directory.
    # Keep alternate/baseline EXEs inside staging to isolate config writes too.
    $isolatedExe=Join-Path $stage 'fallout-hud-baseline.exe'
    Copy-Item -LiteralPath $Executable -Destination $isolatedExe -Force
    $Executable=$isolatedExe
}
$keys=@('FALLOUT_HD_HUD_PREVIEW','FALLOUT_HD_HUD_PANEL_EXPECT','FALLOUT_HD_HUD_PANEL_ASSET',
    'FALLOUT_HD_MENU_PREVIEW','FALLOUT_HD_WORLD_PREVIEW','FALLOUT_HD_PLAYER_PREVIEW','FALLOUT_HD_RAT_PREVIEW','FALLOUT_HD_MENU_EXPECT_HD')
$saved=@{}
foreach($key in $keys){$saved[$key]=[Environment]::GetEnvironmentVariable($key,'Process');[Environment]::SetEnvironmentVariable($key,$null,'Process')}
try {
    if($Mode -eq 'hud'){
        $env:FALLOUT_HD_HUD_PREVIEW=$out
        $env:FALLOUT_HD_HUD_PANEL_EXPECT=$ExpectedPanel
        if($PanelAsset){$env:FALLOUT_HD_HUD_PANEL_ASSET=$PanelAsset}
    } else {$env:FALLOUT_HD_MENU_PREVIEW=$out;$env:FALLOUT_HD_MENU_EXPECT_HD='1'}
    $proc=Start-Process -FilePath $Executable -WorkingDirectory $stage -WindowStyle Hidden -PassThru
    if(!$proc.WaitForExit(120000)){Stop-Process -Id $proc.Id -Force;throw 'Own HUD preview timed out.'}
    $proc.Refresh()
    Add-Type -AssemblyName System.Drawing
    foreach($bmp in Get-ChildItem -LiteralPath $out -Filter '*.bmp' | Where-Object {-not $SkipPng}){
        $im=[Drawing.Image]::FromFile($bmp.FullName)
        try{$im.Save([IO.Path]::ChangeExtension($bmp.FullName,'.png'),[Drawing.Imaging.ImageFormat]::Png)}finally{$im.Dispose()}
    }
    $checks=@(Get-Content (Join-Path $out 'checks.txt'))
    if($Mode -eq 'menu'){$checks+=@(Get-Content (Join-Path $out 'integration.txt'))}
    $passed=@($checks|Where-Object{$_ -match '^PASS '}).Count
    $failed=@($checks|Where-Object{$_ -match '^FAIL '}).Count
    $checks|Where-Object{$_ -match '^(FAIL|TOTAL)'}
    [ordered]@{executable=$Executable;sha256=(Get-FileHash $Executable).Hash;passed=$passed;failed=$failed;exit_code=$proc.ExitCode;runtime=$stage}|
        ConvertTo-Json|Set-Content (Join-Path $out 'verification.json') -Encoding utf8
    if($failed -or $proc.ExitCode -ne 0){throw "Preview failed: $passed PASS, $failed FAIL, exit $($proc.ExitCode)"}
    Write-Output "$passed PASS, $failed FAIL; $out"
} finally {foreach($key in $keys){[Environment]::SetEnvironmentVariable($key,$saved[$key],'Process')}}
