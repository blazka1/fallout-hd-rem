Pistol iteration and v2 inventory integration — 14 November 2026

Geometry reference experiments: qwen-pistol-geometry*.py and raw-preview*.py. Several interrupted attempts are retained; successful first raw preview is qwen21-raw-preview-v5-20261114.
Deterministic mirror and comparison: build/hd-inventory-comparisons/pistol-geometry-20261114.
current-plus-details.py -> qwen21-current-hd-details-v6-20261114: preserve installed v1 geometry, borrow selective new details. User liked the result.
subtle-rust.py -> qwen21-subtle-rust-v7-20261114: very slight rust added at user request.
User requested final inventory/HUD/cursor integration of this latest version.

prepare-v2.py: deterministic ComfyUI alpha cleanup/crop/downscale and lossless F1HD packing into assets/hd/inventory/10mm-pistol/v2. Do not rerun over the chosen manifest casually; preparation writes selection status.
install-v2.ps1 -TestManifest <successful PID8 loaded test manifest>: validates hashes/header, refuses running game, backs up and replaces only runtime pistol.rgba. EXE/knife/knuckles hashes verified unchanged.
Test runner: work/hd-inventory-brass-knuckles/test.ps1 -ItemPid8 (PowerShell syntax: -ItemPid 8). Candidate uses -AssetPath; installed verification uses actual default runtime asset.

Reports and final receipt: build/hd-inventory-pistol/v2-20261114/integration.json.
No engine source, original DAT, gameplay, save or shared menu changes. No whole-runtime preparation.
