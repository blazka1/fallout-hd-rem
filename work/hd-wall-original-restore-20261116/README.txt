Native wall restoration, 16 November 2026

User rejected Blender redesign and requested original sprites through SeedVR2 -> Qwen 2.1.
62 original wall sprites + 3 original upper-cutaway tile sprites. Original FRM metadata and
binary alpha are retained exactly at x4, including original frame registration and seams.
No new topology, geometry, wall placements, collision changes or EXE changes.
Door object 252 is the sole alpha exception: original ca036 texture is clipped by
the previously user-approved A clearance mask, keeping the metal frame exposed.
It stays in its existing 512x512 atlas with the unchanged 124x480 registered crop.

All 65 canonical sprites are fully visible in the five original connected wall neighborhoods
and the three-tile panel. Crops were checked pixel-for-pixel against the source originals.
SeedVR2 x4: 1 step, cfg 1, Euler/simple. Qwen 2.1 INT8: 25 steps, cfg 1, Euler/simple,
reference conditioning + empty output latent, denoise 1, CPU KV cache. Original Canny
structure control strength 0.9, start 0, end .85. Resolution 1200x800 padded to1216x800
for walls; 1152x256 for caps. No aspect-ratio distortion.

Assembly averages Seed/Qwen detail, restores 85 percent of the original low-frequency
light/color (Gaussian sigma 8 HD pixels), and protects original-color boundary pixels.
Original nearest-neighbor alpha is reattached. These conservative restrictions deliberately
avoid previous geometric redesign. Exact alpha does not alone prove visual quality: inspect
the actual SDL game frames in build/hd-wall-original-restore-20261116/after-v1.

Previous Blender source/models/textures remain in assets/hd/v13ent/blender-cave-v3.
Before integration, all 537 affected runtime images + manifest are copied to
build/backups/before-original-seed-qwen-v1-20261116 with SHA256 receipts.
Only affected images and the merged live manifest are installed. Other art and EXE retained.

Reproduction: pipeline.py prepare; pipeline.py seed; pipeline.py qwen-input;
inspect original-canny maps; pipeline.py qwen --only wall-01; inspect pilot;
pipeline.py qwen; assemble.py; test.ps1 -OutputDirectory <absolute after-v1 folder>;
review.py; inspect frames; install.py. Generation resumes saved Comfy prompt IDs.
No shared-queue cancellation or server restart.

Regression adaptation: the installed engine's geometry test assumes placement sprites
must differ from their base HD sprites. Native restoration intentionally makes these
the same, producing 40 failures of that obsolete difference assertion and 1079 passes.
An isolated test-only source copy replaces that assertion with a stricter relevant
check: visible HD detail versus classic FRM inside pixels owned by each tested wall.
All other source files match the hashes used to build the installed EXE. This test
binary is NOT installed. Its full 1119 checks must pass, and all 117 fixed-view SDL
captures must be pixel-identical to the installed EXE's captures of this asset set.
38 other diagnostic captures select objects through std::set<Object*> and therefore
choose different camera positions between processes. Their own in-engine assertions
still run; these sampled views are retained but not paired for pixel comparison.
Both raw and adapted results are retained, without relabeling the old failures.
To reproduce the adapted validation after the stock capture: build-test.ps1 -ProjectRoot
<project absolute path>; validate.ps1; verify-test-equivalence.py. validate.ps1 restores
the stock EXE in the isolated runtime in a finally block. install.py requires the
adapted 1119/0 report, exact equality of 117 fixed captures, and unchanged stock EXE hashes.
