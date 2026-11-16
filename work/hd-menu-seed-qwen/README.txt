Main-menu helmet portrait: sequential SeedVR2 -> Qwen Image 2.1 experiment.
Output: assets/generated/main-menu/seed-qwen-20261114-v1
Source: existing original mainmenu.frm export, crop x8 y12 width380 height456.
This is the portrait region used by the current adaptive menu, not a recreation
of the old screen with embedded buttons. No current menu/runtime assets changed.

SeedVR2 3B INT8: 1520x1824, seed14112026, 1 step, cfg1, Euler/simple,
tiled VAE512/overlap128, no post color correction.
Qwen Image2.1 INT8 + Qwen3VL8B INT8: the Seed output is the actual image reference.
Working size1600x1920, seed14112026, 25steps, cfg1, Euler/simple, denoise1,
CPU reference cache, tiled VAE512/overlap128. Final1800x2160 is a Lanczos
resize to the existing menu asset dimensions, not an additional AI upscale.

Each stage stores prompt-api.json, workflow.json, run.json, history.json,
result.json and images. Use collect for an existing run; never resubmit blindly.
pipeline.py runs in the already installed ComfyUI standalone Python environment.
Python orchestrates the API and makes the comparison sheet; all artistic
processing and crop/scale operations in the production image use ComfyUI nodes.
Comparison: original enlarged nearest-neighbor, Seed, then sequential Qwen.
This task creates a review candidate only; installation is a separate step.
