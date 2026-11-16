Component: Blender cave walls V3, 15 November 2026.

Scope: expand the accepted blender-corner-v2 natural stone to all 417 registered
cave-wall placements, plus the 9 upper cutaway tile images. The approved vault
door-side rock contour is protected. No map, gameplay, EXE or registry changes.

Authoring:
  prepare.py snapshots the current shared runtime and creates an isolated copy.
  analyze.py inventories original FRM placements and connected cave surfaces.
  geometry.py derives smoothed support/height guides from the original footprint.
  scene.py constructs continuous 3D faces and crowns in Blender, sculpts broad
  ridges and seeded open fractures, then renders with the calibrated CE camera.
  One common mesh/material/render supplies all sprite slices. The model is not
  an image atlas stretched over individual FRM masks. Actual planes and normals
  supply relief and illumination. Crown and face share vertex indices.
  cap-scene.py bakes the same stone shader on a horizontal plane; cap.py prepares
  periodic registration on the real (48,-12), (32,24) floor lattice. A periodic
  version of the 120x120 reference detail avoids crop-edge seams on the cap.
  pack.py cuts registered canvases, joins the back of the crown to the common
  cap field, and quantizes NEW alpha to native 4x4 blocks required by CE.

Material: loaded from the accepted natural corner .blend, originally authored
with neutral gray procedural stone and 42% reference detail from the user's
HD rock03, crop [158,210,278,330]. Roughness, grain scale and sharp-angle normals
retain that style. Whole-map directional lights prevent separate-render seams.
The denser full-cave mesh uses a 55-degree sharp-edge threshold, checked against
the accepted corner at full resolution, to remove distracting triangle shading
while retaining the deep faults. The original corner used 28 degrees.
Geometry seed: 15112503. Blender 5.2.4 LTS, Cycles, 24 samples with denoising.
CPU was used for initial studies; the final fit uses OptiX on the RTX 4060 after
checking the shared ComfyUI queue and confirming no other chat is generating.
The projected displacement is bounded by distance to the supported silhouette;
outer boundaries are protected during mesh decimation to avoid canvas clipping.
The final atlas is rendered with scene.py -- tiles gpu as overlapping camera
regions of the SAME complete scene, then assembled by stitch.py. This avoids
the memory cost of denoising the entire 10920x5460 atlas at once. The orthographic
projection is checked for every region; lights and material coordinates do not
move. Shared borders are composited with premultiplied alpha and smooth weights,
without any color correction or image warp. Region hashes are in tile-layout.json.

Generated scene and data:
  assets/generated/v13ent-wall-blender/cave-v3-20261115/
Game screenshots/checks:
  build/hd-wall-blender-cave-20261115/
Selected package after successful integration:
  assets/hd/v13ent/blender-cave-v3/

Verification: audit.py checks native alpha, canvas coverage, exact common-render
overlaps, hashes of protected assets and unchanged EXE/registries. test.ps1 runs
the actual SDL world preview in the isolated runtime. review.py creates honest
before/after comparisons and compares all available classic frames exactly.
Installation is gated on those results; see task.json and integration.json for
the actual installed state and counts. AGENTS.md is not edited automatically.

Rollback: rollback.ps1 -CheckOnly verifies every protected backup/current hash;
rollback.ps1 restores only this component's files and manifest when the game is
closed. It refuses to overwrite any subsequent changes.
