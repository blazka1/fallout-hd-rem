# Deterministic sprite-sheet extraction/registration. Artwork is ImageGen's.
# System.Drawing resamples RGBA with premultiplied alpha; no artistic relighting.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$project=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$run=Join-Path $project 'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
$output=Join-Path $project 'assets/hd/player-male-vault13/lighting-v2-x4'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$plan=Get-Content (Join-Path $run 'registration-plan.json') -Raw | ConvertFrom-Json
foreach($entry in $plan.entries){
    $path=Join-Path $output ($entry.stem+'.png')
    if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
    $source=[Drawing.Image]::FromFile($entry.atlas)
    $canvas=[Drawing.Bitmap]::new(($entry.native_dimensions[0]*4),($entry.native_dimensions[1]*4),[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g=[Drawing.Graphics]::FromImage($canvas)
    try {
        $g.Clear([Drawing.Color]::Transparent)
        $g.CompositingMode=[Drawing.Drawing2D.CompositingMode]::SourceCopy
        $g.CompositingQuality=[Drawing.Drawing2D.CompositingQuality]::HighQuality
        $g.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::Half
        $t=$entry.target_rect;$s=$entry.source_crop
        $destination=[Drawing.RectangleF]::new($t[0],$t[1],$t[2],$t[3])
        $sourceRect=[Drawing.RectangleF]::new($s[0],$s[1],$s[2],$s[3])
        $g.DrawImage($source,$destination,$sourceRect,[Drawing.GraphicsUnit]::Pixel)
        $canvas.Save($path,[Drawing.Imaging.ImageFormat]::Png)
    } finally {$g.Dispose();$canvas.Dispose();$source.Dispose()}
}
Write-Output 'Registered 54 x4 RGBA sprites; original native dimensions/anchors retained.'
