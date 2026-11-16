Native cave walls and ceiling: neutral-grey material match, 16 November 2026.

User requested removing blue and matching brightness to existing adjacent rocks,
while retaining the accepted original geometry and seams. This component updates
the 537 images from original-seed-qwen-v1. Every alpha byte, dimension and registry
is unchanged, including the approved clearance around the vault door.

Walls: native ComfyUI nodes convert RGB to Rec.709 luminance (0.2126/0.7152/0.0722),
then apply one shared linear tone curve Yout=1.18*Y+4 in 8-bit values. All RGB
channels become identical. No geometry generation or spatial filtering on walls.
Black transparent pixels remain transparent; alpha comes from the existing files.
The same pointwise transform applies at every shared wall edge. The reference
stones were sampled from the live runtime; their images are not altered.

Ceiling/cutaway: three original tile sources are newly upscaled with SeedVR2 x4,
neutralized through the shared curve, then restored with Qwen Image 2.1 and the
current grey-rock reference. 25 steps, cfg1, Euler/simple, denoise1 with reference
conditioning, CPU KV cache. Original Canny control strength1 from start to end.
Qwen material is neutralized and matched to corrected baseline brightness, then
used at 25 percent in the interior. An 8-HD-pixel protected edge and 16-pixel fade
retain the shared edge colors. Current alpha and tile registration are exact.
All art/color processing uses ComfyUI; Python orchestrates, builds masks, packs
RGBA8, and verifies the result. Comfy workflows, prompts and job receipts retained.

Validation reuses the test-only EXE from the previous original restoration, whose
rendering/game source matches the live EXE. Its single changed assertion compares
wall HD to classic pixels within the wall's own cells, allowing identical base
and placement HD textures. The installed stock EXE remains unchanged. validate.ps1
restores the stock EXE in the isolated runtime even on failure. 1119 checks and
18 exact classic-frame comparisons are required before installation.

Baseline images: build/hd-wall-original-restore-20261116/after-v1, verified against
current live art hashes before use. New captures: build/hd-wall-grey-match-20261116/after-v1.
Previous blue restoration and Blender packages remain in assets/hd/v13ent/.
Runtime backup: build/backups/before-wall-grey-match-20261116.

Reproduction: pipeline.py prepare; pipeline.py colour; pipeline.py seed;
inspect controls/references; pipeline.py qwen; inspect raw result;
finish.py fit; finish.py stage; validate.ps1; review.py; inspect game frames;
install.py; rollback.ps1 -CheckOnly.
