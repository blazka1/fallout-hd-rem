FALLOUT 1 CE — V13ENT STATIC BASE HYBRID TEXTURES, X4

Status: artistic candidate; engine integration and in-game validation pending.
159 existing resources: 57 floor tiles, 70 walls, 32 scenery images.
99 new direct ComfyUI/SDXL outputs, 55 new floor-edge-prepared outputs,
two individual ImageGen + ComfyUI overrides (rock03 and cav1000), and
three faithful previous HD mechanical resources. This is 154 new Comfy
resources + two individual hybrids + three preserved prior HD outputs.
grt2000 retains its cross-grid grating; doorcomp retains its display and
buttons; v13secr3 retains its sill and pillar panel structure/shading.
The stronger new mechanical candidates were rejected for those changes.
Original canvas, frame offsets and exact nearest-neighbor alpha are retained.
The assembly only copies validated PNG bytes; it performs no artistic edits.

This package does not replace animated doors, critters, items, invisible
blockers, exit markers or script-created dependencies. It does not add
decorations, alter maps/prototypes or change collision and pathfinding.
This is the static base subset of the first cave, not the complete remaster.

Per-resource metadata contains original inventory records, selected hashes,
actual generation run references, Comfy prompt IDs and workflow/API/history hashes.
Review visual quality in the actual map, especially wall/floor seams and lighting.
Do not overwrite this version with different bytes; use a new version directory.
