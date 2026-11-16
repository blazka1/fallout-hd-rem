Natural cave wall — Blender corner V2, 15 November 2026.

User rejected V1 as a masonry wall of separate plates. V2 replaces the
individual inset polygon stones with a continuous eroded rock mesh.
The front, bend and crown share vertices. Broad irregular relief and
14 partial fault lines replace the repeated outlines around every slab.
The calibrated camera, supported footprint and endpoint shoulders remain.
The dense continuous sculpt is reduced to irregular fracture planes;
normal smoothing stops at 28-degree edges, keeping firm changes of plane.

Rejected offline revisions: 1 had uniform cell-like texture; 2 was too
soft; 3 exposed the triangulation. The selected revision combines angle-
limited normals and restrained reference material. These rejected renders
were not installed. Only the selected version is taken through SDL checks.

Material references: current cave geo-rock-01 (style-match-v2-20261115)
and original-derived HD rock03 from v14-campfire-x4. Color is restrained
cool gray, with mid-scale mineral chips and reduced sand-like grain.
Voronoi is used only for small material chips, not for wall construction.
A fully opaque 120x120 HD patch from rock03, crop (158,210)-(278,330),
provides 42% of the material color plus restrained bump using Blender's
world-space box projection. The exact source/crop is verified in
material-provenance.json and packed into the .blend. Geometry and sprite
masks are still the new mesh, not inherited from that material patch.
No relief image atlas or AI remapping is involved. Authoring is Blender 5.2.4 LTS,
Cycles CPU (6 threads, 40 samples), deterministic seed 15112026.

Eleven placement-specific wall sprites replace the previous Blender pilot:
327,328,349,350,351,365,366,415,434,452,463. They are cut from one render.
Canvas sizes, offsets, FIDs/PIDs, placement order and collision stay fixed.
Interior alpha is projected from the new mesh, quantized to the native
pixel grid required by the existing loader. The two open ends transition
to the surrounding existing wall over 28 native horizontal pixels.
That attachment color is the verified pre-V1 V4 backup, so the rejected
plate imagery is not repeatedly blended into the new ends.

Before captures are actual SDL outputs of the installed Blender V1.
prepare.py verifies the exact EXE and all 1360 non-manifest art files
against that tested runtime before reusing those images.
Screenshots in the comparison receive only an identical crop and labels.
No brightness or color editing is applied to the game screenshots.

Outputs: assets/generated/v13ent-wall-blender/natural-v2-20261115/.
Selected component: assets/hd/v13ent/blender-corner-v2/.
Tests/comparisons: build/hd-wall-blender-natural-20261115/.
The actual final status, audit, checks and installation are recorded
in task.json and build/hd-wall-blender-natural-20261115/integration.json.

Shared EXE, HD rats, menu, door rock, map and other imagery are preserved.
AGENTS.md and HD-TEXTURE-GUIDE.md are not edited by this task.
rollback.ps1 -CheckOnly validates the reversible 12-file backup.
Actual rollback refuses later changes and requires closed Fallout.
