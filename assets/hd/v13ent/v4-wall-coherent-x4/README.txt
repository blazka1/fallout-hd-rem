FALLOUT 1 CE — V13ENT STATIC BASE HYBRID TEXTURES, X4

Status: candidate; engine integration and in-game visual validation pending.
Derived from the selected v3 package. All 159 resources remain existing
static base art: 57 floor tiles, 70 walls and 32 scenery images.

This revision prepares all 70 walls through the recorded deterministic
ComfyUI coherence workflow: the recorded original/faithful macro baseline
with medium detail from the selected v3 donor. Per-wall metadata identifies
the actual baseline and its source hash. No new scene geometry is created.
The other 89 PNGs and their metadata are copied byte-for-byte from the
parent. Existing floor coherence, two hybrid overrides and three faithful
mechanical selections remain as recorded in that parent package.

Every selected image was validated for exact x4 dimensions and original
nearest-neighbor alpha. Baselines were checked at their recorded original
native or previous HD dimensions. Wall metadata preserves original
art provenance and appends actual prompt/workflow/history and input hashes.
Assembly copies PNG bytes and performs no artistic image editing.

Animated doors, critters, items, invisible blockers, exit markers and
script-created dependencies remain excluded. No map, prototype, collision,
pathfinding, HUD or menu content is changed. This is not the full remaster.
A parent resource's previous integration status does not validate this new
wall candidate; review seams, lighting and appearance in the actual game.
Do not overwrite this version with different bytes; use a new directory.
