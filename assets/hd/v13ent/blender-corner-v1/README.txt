Blender wall corner pilot — 15 November 2026.

Scope: one connected wall bend to the right of the Vault 13 entrance.
The solid mesh, fractured face wedges, crown, material, camera and lights
are authored in scene.py. Blender 5.2.4 LTS renders them through Cycles
on CPU (6 threads, 40 samples). No ComfyUI job, AI atlas or texture warp.

The orthographic camera is calibrated against CE's actual projected
ground vectors (48,-12) and (32,24). camera-calibration.json contains
measurements from Blender's world_to_camera_view, error <0.001 native px.

Eleven placement-specific wall canvases receive slices of the same
render: objects 327,328,349,350,351,365,366,415,434,452,463.
Their existing FID/PID, dimensions, offsets and order remain unchanged.
Interior alpha comes from the NEW render. The current wall loader requires
binary alpha constant over each 4x4 HD cell, so the projected silhouette
is quantized to native pixels. It is not stamped with the original mask.
Only the two open ends transition into the previous V4 material, over
28 native horizontal pixels. The approved door rock remains separate.

Rejected revision-1: too regular plate outlines; two slices rejected by
CE due to soft alpha (1115 PASS, 2 FAIL; not installed).
Rejected revision-2: 1119 PASS, but crown cropped into stairs by the
individual sprite canvases. This exposed the need for a lower crest.
Revision-3: lower crest within every canvas, continuous physical crown.
1119 PASS, 0 FAIL on the fresh rat-integration EXE, but a visible step
remained at the left transition from the higher old rim.
Revision-4: physical shoulders rise into the old rim at both endpoints.
Final status and actual tests/installation are in task.json/integration.json.

During this task the rat chat installed a new EXE. refresh-runtime.py
adopts its completed integration into the isolated test runtime. All
20 required before captures match pixel-for-pixel. The final comparison
uses that chat's actual SDL before captures on the same final EXE.
runtime-refresh.json records their provenance. We do not overwrite EXE.

Paths:
assets/generated/v13ent-wall-blender/pilot-20261115/ — editable .blend,
raw render, calibrated registration, slices and rejected revisions.
build/hd-wall-blender-pilot-20261115/ — SDL before/after, audit and comparison.
assets/hd/v13ent/blender-corner-v1/ — selected, installed component.

This is an artistic prototype of ONE section. It does not convert the
remaining walls, global cutaway floor tiles or the game to 3D.
Scene collision, map objects, F11 original and EXE are kept unchanged.
AGENTS.md and HD-TEXTURE-GUIDE.md are not updated by this task.

Reproduce (from project root):
  Blender -b --factory-startup --python work/hd-wall-blender-pilot-20261115/scene.py
  Python work/hd-wall-blender-pilot-20261115/pack.py
  Python work/hd-wall-blender-pilot-20261115/audit.py
  Run test.ps1 only with no other Fallout instance. Do not cancel other chats.
  review.py after-v4 uses unchanged SDL captures, identical crop and scale.

Rollback: rollback.ps1 -CheckOnly verifies the backup without writing.
Actual rollback requires closed Fallout and exact current hashes; it
refuses to overwrite later changes. Do not run older V4 rollback over
this component. Return this component first if rolling back further.
