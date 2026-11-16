Brass Knuckles HD — 2026-11-13

Original: PID21, inventory FID0x0700008C, art/inven/brsnuck.frm, 81x65; world FID47.
Local generation: 20261113/seed-knuckles.py and qwen-knuckles.py (prepare/submit/collect). Never resubmit a saved run blindly. ComfyUI localhost:8188.
Selected Qwen material: assets/hd/inventory/brass-knuckles/v1/knuckles-hd-x4.png, 324x260 RGBA.
prepare-selected.py performs deterministic ComfyUI cleanup and lossless F1HD packing. Four finger holes and exact PNG/RGBA equality recorded in qa.json.

Implementation: third independent Asset record in game/hd_hud.cc. Same existing HUD, inventory and cursor rendering paths as Knife and 10mm Pistol. No weapon stats, maps, save format or prototype changes. Original DAT FRM fallback retained.
Test harness accepts ItemPid 4,8,21, checks appropriate FID and unarmed punch animation. Starting Max Stone inventory already contains the knuckles. A test-only temporary fixture supports otherwise absent items and does not save.

Build: work/hd-world-pilot/tools/build.ps1
Stage completed EXE beside runtime fallout.cfg as fallout-hud-test.exe.
Preinstall test: test.ps1 -Executable runtime/hd-world-pilot/fallout-hud-test.exe -AssetPath assets/hd/inventory/brass-knuckles/v1/knuckles.rgba -OutputDirectory build/hd-inventory-brass-knuckles/preview/v1-loaded
Install: install.ps1 -TestManifest build/hd-inventory-brass-knuckles/preview/v1-loaded/manifest.json
Installer refuses running runtime, validates tested hashes, backs up and installs only EXE plus knuckles.rgba.

Verification: build/hd-inventory-brass-knuckles/integration.json and installation receipt.
Fresh target loaded/missing/corrupt, Knife/Pistol regressions, cave and menu. Tests are programmatic real CE/SDL captures, not a full playthrough.
Source backup: build/backups/before-hd-brass-knuckles-20261113.
Launch: Start-Fallout-HD-World-Pilot.cmd. Restart after an asset or EXE update.
