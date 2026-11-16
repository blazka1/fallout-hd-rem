# V13ENT original reference sample

This is a source-decoding package, not enhanced art. Python 3.10+ and the standard
library are sufficient; no venv or pip packages are required. DAT archives are
opened read-only. All output files are created under the explicit `--output`
directory; an existing file with different bytes is never replaced.

The scanner parsed all 177,224 bytes of `maps/v13ent.map` (version 19), verified
the total of 1,494 root objects and resolved names through the game's LST files.
Inventory payload lengths are selected using the original PRO subtypes.

## Selected originals

| Use | Original resource | FID / tile art ID | Native size | Map use |
| --- | --- | --- | --- | --- |
| First img2img candidate | `art/scenery/rock03.frm` | FID 33554605 | 123 × 103 | 13 objects |
| Wall strip reference | `art/walls/ca063.frm` | FID 50331732 | 36 × 168 | 6 objects |
| Floor reference | `art/tiles/cav1000.frm` | tile ID 21 | 80 × 36 | 96 floor cells |

The large rock is a complete static silhouette. The wall is a narrow assembly
strip; its contact sheet is a catalog, not one connected object for img2img.
All selected art has one frame. `sample.json` records exact map object offsets,
coordinates, FIDs/PIDs, source archive offsets, original FRM SHA256, frame shifts,
direction offsets, dimensions, PNG SHA256 and the original palette identity.

Inside `v13ent-first-asset/`:

- `rgba/art/scenery/rock03.frm.png`: primary transparent RGBA reference.
- `rgba/art/walls/ca063.frm.png`: original transparent wall strip.
- `rgba/art/tiles/cav1000.frm.png`: original transparent floor tile.
- `png/`: indexed PNG equivalents, retaining the palette indices.
- `contact/`: unscaled wall, rock and floor contact sheets for human selection.
- `raw/`: exact decompressed original MAP, PAL, LST, PRO and selected FRM bytes.
- `metadata/` and `sample.json`: frame registration and provenance.

Palette conversion matches CE's RGB6-to-RGB8 shift by 2. Index 0 is transparent;
all other indices are opaque. No runtime lighting or animated palette cycles
are applied. No scaling, filtering, generation, painting or retouching occurred.
Individual exported indexed and RGBA PNGs were decoded again and verified pixel
for pixel against the original FRM raster; PNG CRC and dimensions also checked.

## Reproduce in PowerShell

Run this single command (all source paths are read-only):

```powershell
python "C:/Users/Administrator/Desktop/Fallout1-Godot/tools/asset-pipeline/cave_reference.py" --archive "C:/Users/Administrator/Desktop/Fallout1-Godot/FALLOUT (extract.me)/MASTER.DAT" --archive "C:/Users/Administrator/Desktop/Fallout1-Godot/FALLOUT (extract.me)/CRITTER.DAT" --output "C:/Users/Administrator/Desktop/Fallout1-Godot/assets/reference/v13ent-first-asset" --export-sample
```

An identical rerun is safe. To retain an alternative selection, use a new output
directory. Omitting `--export-sample` prints actual static-object/floor candidates;
adding `--output` then saves the parsed MAP and candidate JSON instead.

Scope: 18 selected static-art resources and their source evidence. This is not a
complete playable-map dependency export, replacement renderer or enhanced asset.
The source archives remain necessary for further extraction.

