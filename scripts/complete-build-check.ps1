[CmdletBinding()]
param(
    [string]$ProjectRoot=(Split-Path $PSScriptRoot -Parent),
    [Parameter(Mandatory)][string]$RunDirectory,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{0,79}$')][string]$Component,
    [ValidateSet('Passed','Failed')][string]$Outcome='Failed',
    [string]$BackupDirectory='',
    [string[]]$TemporaryFiles=@(),
    [switch]$KeepPrevious
)
# Call only after every consumer/comparison has finished. No background sweeper.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$project=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
$build=Join-Path $project 'build'
function Checked-Path([string]$path,[string]$parent) {
    $full=[IO.Path]::GetFullPath($path)
    if(-not $full.StartsWith($parent+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Outside allowed directory: $full" }
    $ancestor=$full
    while($ancestor) {
        if([IO.File]::Exists($ancestor) -or [IO.Directory]::Exists($ancestor)) {
            if([IO.File]::GetAttributes($ancestor) -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $ancestor" }
        }
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
    }
    return $full
}
function Hash-File([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
function Write-Json([string]$path,$value) {
    $tmp=$path+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
    try { $value|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $tmp -Encoding utf8; Move-Item -LiteralPath $tmp -Destination $path -Force }
    finally { if(Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force } }
}
function Pixel-Hash([string]$path) {
    $bitmap=[Drawing.Bitmap]::new($path); $locked=$null
    try {
        $rect=[Drawing.Rectangle]::new(0,0,$bitmap.Width,$bitmap.Height)
        $locked=$bitmap.LockBits($rect,[Drawing.Imaging.ImageLockMode]::ReadOnly,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $hash=[Security.Cryptography.SHA256]::Create()
        try {
            $rowBytes=$bitmap.Width*4
            if($locked.Stride -eq $rowBytes) {
                $bytes=New-Object byte[] ($rowBytes*$bitmap.Height)
                [Runtime.InteropServices.Marshal]::Copy($locked.Scan0,$bytes,0,$bytes.Length)
                $digest=$hash.ComputeHash($bytes)
            } else {
                $row=New-Object byte[] $rowBytes
                for($y=0;$y -lt $bitmap.Height;$y++) {
                    [Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($locked.Scan0,$y*$locked.Stride),$row,0,$rowBytes)
                    $null=$hash.TransformBlock($row,0,$rowBytes,$row,0)
                }
                $null=$hash.TransformFinalBlock([byte[]]@(),0,0); $digest=$hash.Hash
            }
            return "$($bitmap.Width)x$($bitmap.Height):$([BitConverter]::ToString($digest).Replace('-',''))"
        } finally { $hash.Dispose() }
    } finally { if($locked) {$bitmap.UnlockBits($locked)}; $bitmap.Dispose() }
}
function Is-CapturePath([string]$path,[string]$parent) {
    $relative=$path.Substring($parent.Length+1).Replace('\','/')
    return $relative -notmatch '(^|/)(_deps|msvc|test-msvc|CMakeFiles|runtime[^/]*|data|assets|backup[^/]*|savegame)(/|$)'
}
function Checked-Run([string]$path) {
    $full=Checked-Path $path $build
    $relative=$full.Substring($build.Length+1).Replace('\','/')
    if(($relative -notmatch '/' -and $relative -ne 'hd-menu-preview') -or -not (Is-CapturePath $full $build) -or $relative.StartsWith('.retention/')) {throw "Not a dedicated capture directory: $full"}
    return $full
}
function Files-Record([string]$directory,[string[]]$extensions,[bool]$capturesOnly=$false) {
    $records=@()
    foreach($file in Get-ChildItem -LiteralPath $directory -Recurse -File -Force) {
        $null=Checked-Path $file.FullName $directory
        if($capturesOnly -and -not (Is-CapturePath $file.FullName $directory)) {continue}
        if($file.FullName -match '[\\/]SAVEGAME[\\/]' -or $file.Extension -notin $extensions) { continue }
        $records+=@{path=$file.FullName;bytes=$file.Length;sha256=(Hash-File $file.FullName)}
    }
    return $records
}
$run=Checked-Run $RunDirectory
if(-not (Test-Path -LiteralPath $run -PathType Container)) {throw 'RunDirectory must already exist'}
# Reject links anywhere in the requested tree before enumerating/converting captures.
foreach($entry in Get-ChildItem -LiteralPath $run -Recurse -Force) {
    if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw "Reparse point: $($entry.FullName)"}
}
$manifestPath=Join-Path $run 'retention-manifest.json'
$prior=$null
if(Test-Path -LiteralPath $manifestPath) {
    $prior=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
    if($prior.component -ne $Component) {throw 'RunDirectory belongs to another component'}
}
$stateDir=Join-Path $build '.retention'
$null=Checked-Path $stateDir $build
New-Item -ItemType Directory -Path $stateDir -Force|Out-Null
$lockPath=Join-Path $stateDir 'writer.lock'
$null=Checked-Path $lockPath $stateDir
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$deleted=[Collections.Generic.List[object]]::new()
$skipped=[Collections.Generic.List[string]]::new()
function Remove-Recorded($record,[string]$parent) {
    $path=Checked-Path $record.path $parent
    if($path -match '[\\/]SAVEGAME[\\/]' -or [IO.Path]::GetExtension($path) -in '.sav','.dat','.json','.txt','.md','.log','.tsv','.csv','.cc','.h','.py','.ps1','.blend') {throw "Protected record: $path"}
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)) {return}
    $file=Get-Item -LiteralPath $path
    if($file.Length -ne $record.bytes -or (Hash-File $path) -ne $record.sha256) {$skipped.Add($path);return}
    $null=Checked-Path $path $parent
    Remove-Item -LiteralPath $path -Force
    $deleted.Add(@{path=$path;bytes=$file.Length})
}
try {
    if($BackupDirectory -and $Outcome -ne 'Passed') {throw 'Backup rotation requires successful validation and installation'}
    # Ownership is global: parent/child output trees cannot belong to different runs/components.
    foreach($registry in Get-ChildItem -LiteralPath $stateDir -Filter '*.json' -File) {
        $null=Checked-Path $registry.FullName $stateDir
        $other=Get-Content -LiteralPath $registry.FullName -Raw|ConvertFrom-Json
        foreach($registered in $other.runs) {
            $registeredDir=Checked-Run $registered.directory
            if($registeredDir -eq $run) {
                if($other.component -ne $Component){throw 'Output is owned by another component'}
            } elseif($run.StartsWith($registeredDir+'\',[StringComparison]::OrdinalIgnoreCase) -or $registeredDir.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Overlapping output directories in global retention registry'}
        }
        if($BackupDirectory -and $other.backup) {
            $requestedBackup=Checked-Path $BackupDirectory (Join-Path $build 'backups')
            $registeredBackup=Checked-Path $other.backup.directory (Join-Path $build 'backups')
            if(($requestedBackup -eq $registeredBackup -and $other.component -ne $Component) -or $requestedBackup.StartsWith($registeredBackup+'\',[StringComparison]::OrdinalIgnoreCase) -or $registeredBackup.StartsWith($requestedBackup+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Overlapping/foreign backup ownership'}
        }
    }
    $statePath=Join-Path $stateDir ($Component+'.json')
    $null=Checked-Path $statePath $stateDir
    $state=@{component=$Component;runs=@();backup=$null}
    if(Test-Path -LiteralPath $statePath) {
        $loaded=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
        if($loaded.component -ne $Component) {throw 'Invalid component registry'}
        $state.runs=@($loaded.runs);$state.backup=$loaded.backup
    }
    foreach($old in $state.runs) {
        if($run -ne $old.directory -and ($run.StartsWith($old.directory+'\',[StringComparison]::OrdinalIgnoreCase) -or $old.directory.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase))) {throw 'Overlapping registered run directories'}
    }
    foreach($bmp in Get-ChildItem -LiteralPath $run -Filter '*.bmp' -Recurse -File) {
        if(-not (Is-CapturePath $bmp.FullName $run)) {continue}
        $source=Checked-Path $bmp.FullName $run
        $sourceHash=Hash-File $source
        $png=[IO.Path]::ChangeExtension($source,'.png')
        $null=Checked-Path $png $run
        $pixels=Pixel-Hash $source
        $needsPng=-not (Test-Path -LiteralPath $png)
        if(-not $needsPng -and (Pixel-Hash $png) -ne $pixels) {
            $owned=@($prior.captures|Where-Object {$_.path -eq $png -and $_.sha256 -eq (Hash-File $png)})
            if(-not $prior -or $owned.Count -ne 1) {throw "Different unowned PNG: $png; BMP preserved"}
            $needsPng=$true
        }
        if($needsPng) {
            $tmp=$png+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
            try {
                $bitmap=[Drawing.Bitmap]::new($source)
                try {$bitmap.Save($tmp,[Drawing.Imaging.ImageFormat]::Png)} finally {$bitmap.Dispose()}
                if((Pixel-Hash $tmp) -ne $pixels) {throw "Lossless conversion failed: $source"}
                Move-Item -LiteralPath $tmp -Destination $png -Force
            } finally {if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
        }
        if((Pixel-Hash $png) -ne $pixels -or (Hash-File $source) -ne $sourceHash) {throw 'Capture changed during finalization'}
        Remove-Recorded @{path=$source;bytes=$bmp.Length;sha256=$sourceHash} $run
    }
    foreach($temp in $TemporaryFiles) {
        $path=Checked-Path $temp $run
        if(-not (Is-CapturePath $path $run)) {throw 'Temporary artifact is in a protected subtree'}
        if([IO.Path]::GetExtension($path) -notin '.exe','.dll','.pdb','.ilk','.rgba','.bin','.fixture','.zip','.7z') {throw "Not an allowed temporary artifact: $path"}
        if(Test-Path -LiteralPath $path -PathType Leaf) { $file=Get-Item -LiteralPath $path; Remove-Recorded @{path=$path;bytes=$file.Length;sha256=(Hash-File $path)} $run }
    }
    $captures=@(Files-Record $run @('.png') $true)
    if($Outcome -eq 'Passed' -and -not $KeepPrevious -and $captures.Count -eq 0 -and @($state.runs|ForEach-Object {$_.captures}).Count -gt 0) {throw 'Empty successful run cannot replace previous captures; no prior PNG were removed'}
    $current=@{component=$Component;directory=$run;outcome=$Outcome;completed_utc=[DateTime]::UtcNow.ToString('o');captures=$captures;storage='PNG; BMP deleted only after decoded-pixel equality'}
    Write-Json $manifestPath $current
    if($Outcome -eq 'Passed' -and -not $KeepPrevious) {
        foreach($old in $state.runs) {
            if($old.directory -eq $run) {continue}
            $oldDir=Checked-Run $old.directory
            if(Test-Path -LiteralPath (Join-Path $oldDir '.keep-build-artifacts')) {continue}
            $owner=Join-Path $oldDir 'retention-manifest.json'
            if(-not (Test-Path -LiteralPath $owner) -or (Get-Content -LiteralPath $owner -Raw|ConvertFrom-Json).component -ne $Component) {throw 'Missing/mismatched ownership of prior run'}
            foreach($record in $old.captures) {
                if([IO.Path]::GetExtension($record.path) -ne '.png') {throw 'Non-PNG in capture registry'}
                if(-not (Is-CapturePath $record.path $oldDir)) {throw 'Protected subtree in capture registry'}
                Remove-Recorded $record $oldDir
            }
        }
    }
    if($BackupDirectory) {
        if($Outcome -ne 'Passed') {throw 'Register/rotate backup only after successful validation and installation'}
        $backupRoot=Join-Path $build 'backups'
        $backup=Checked-Path $BackupDirectory $backupRoot
        if(-not (Test-Path -LiteralPath $backup -PathType Container)) {throw 'BackupDirectory missing'}
        foreach($entry in Get-ChildItem -LiteralPath $backup -Recurse -Force) {if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point in backup'}}
        $owner=Join-Path $backup 'retention-owner.json'
        if((Test-Path -LiteralPath $owner) -and (Get-Content -LiteralPath $owner -Raw|ConvertFrom-Json).component -ne $Component){throw 'Backup belongs to another component'}
        $binaryExtensions=@('.exe','.dll','.pdb','.ilk','.png','.bmp','.rgba','.bin','.fixture','.zip','.7z')
        $newBackup=@{component=$Component;directory=$backup;files=@(Files-Record $backup $binaryExtensions)}
        Write-Json $owner $newBackup
        if($state.backup -and $state.backup.directory -ne $backup -and -not $KeepPrevious) {
            $oldDir=Checked-Path $state.backup.directory $backupRoot
            if($oldDir.StartsWith($backup+'\',[StringComparison]::OrdinalIgnoreCase) -or $backup.StartsWith($oldDir+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Overlapping backups'}
            $oldOwner=Join-Path $oldDir 'retention-owner.json'
            if(-not (Test-Path -LiteralPath $oldOwner) -or (Get-Content -LiteralPath $oldOwner -Raw|ConvertFrom-Json).component -ne $Component) {throw 'Missing/mismatched backup ownership'}
            if(-not (Test-Path -LiteralPath (Join-Path $oldDir '.keep-build-artifacts'))) {
                foreach($record in $state.backup.files) {
                    if([IO.Path]::GetExtension($record.path) -notin $binaryExtensions){throw 'Invalid backup registry extension'}
                    Remove-Recorded $record $oldDir
                }
            }
        }
        $state.backup=$newBackup
    }
    $state.runs=@($state.runs|Where-Object {$_.directory -ne $run})+@($current)
    Write-Json $statePath $state
    $report=@{component=$Component;run=$run;outcome=$Outcome;completed_utc=[DateTime]::UtcNow.ToString('o');png_count=$captures.Count;removed=@($deleted);removed_bytes=($deleted|Measure-Object bytes -Sum).Sum;changed_files_preserved=@($skipped)}
    Write-Json (Join-Path $run 'retention-report.json') $report
    Write-Output "Retention [$Component]: $($captures.Count) PNG; removed $($deleted.Count) files; changed files preserved $($skipped.Count)."
    $buildBytes=(Get-ChildItem -LiteralPath $build -Recurse -File -Force|Measure-Object Length -Sum).Sum
    if($buildBytes -gt 5GB) {Write-Warning "Build exceeds 5 GiB ($([Math]::Round($buildBytes/1GB,2)) GiB). Review component captures/pins; no unregistered files were deleted."}
} finally {$lock.Dispose()}
