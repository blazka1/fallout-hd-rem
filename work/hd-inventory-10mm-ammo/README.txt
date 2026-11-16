10mm JHP / AP â€” HD inventory icons, 14 November 2026

Project root: C:/Users/Administrator/Desktop/Fallout1-Godot
Scope: pilot HUD, inventory list/hand slots and drag cursor.
JHP: PID 29, inventory FID 0x0700001F, art/inven/10mmjhp.frm, 83x58 -> 332x232.
AP: PID 30, inventory FID 0x0700001E, art/inven/10mmap.frm, 83x61 -> 332x244.
Original DAT, prototypes, world icons, saves, item statistics and actions unchanged.

Sources and candidates:
  assets/generated/inventory-10mm-ammo/20261114/{jhp,ap}/
  source/: original FRM/palette/prototype/message bytes, indexed PNG, RGBA, source.json.
  seed/: independent SeedVR2 3B INT8 x4 and Lanczos baseline.
  qwen/: independent Qwen Image 2.1 INT8 original-reference restoration.
  Every run has workflow, API graph, plan, prompt_id, history and result hashes.
  Local ComfyUI 127.0.0.1:8188; no model installation or remote generation.

Selected packages:
  assets/hd/inventory/10mm-jhp/v1/
  assets/hd/inventory/10mm-ap/v1/
  Qwen chosen for coherent contours and restrained metal highlights.
  Seed preserved as comparison; too much glare and invented wear.
  Both retain five rounds: three upright and two lying in the original arrangement.
  JHP remains blue; AP retains its red-copper distinction.
  ComfyUI removed observed alpha <= 8/255 background noise, retained soft edges,
  expanded framing to avoid clipping and scaled to native x4.
  ammo.rgba is F1HD RGBA8, exact decoded ammo-hd-x4.png bytes.

Engine changes (only isolated pilot sources):
  hd_hud.cc: two new entries in the existing item table, now five items.
  hd_hud_test.cc: PID/FID selection, actual ammo objects, non-weapon behavior checks.
  inventry.cc: test-only PID lookup and scrolling to keep returned fixture visible.
  The seven-entry AP test originally returned it below six visible slots; the
  preview harness now scrolls to it. Ordinary inventory scrolling is unchanged.
  source.patch and build/backups/before-hd-10mm-ammo-source-20261114 preserve edits.

Reproduction scripts (use the existing Comfy Python from INVENTOTY_ITEM_CREATE.md):
  20261114/ammo.py export
  20261114/ammo.py submit --item jhp|ap --model seed|qwen
  20261114/ammo.py collect --item jhp|ap --model seed|qwen
  20261114/select.py prepare/collect --item jhp|ap (use recorded threshold/crop)
  20261114/select.py compare
  Existing run.json is never resubmitted. Use new directories for new versions.

Validation and installation:
  work/hd-world-pilot/tools/build.ps1
  verify-final.ps1 -Stage Candidates
  install.ps1 -ItemPid 29 -TestManifest build/hd-inventory-10mm-ammo/preview/final-jhp-loaded/manifest.json
  install.ps1 -ItemPid 30 -TestManifest build/hd-inventory-10mm-ammo/preview/final-ap-loaded/manifest.json
  verify-final.ps1 -Stage Installed
  20261114/finalize.py
  Installer validates loaded tests, exact EXE/asset hashes, F1HD size and runtime
  inactivity, backs up only its destinations and records a receipt.
  It does not run historical prepare-runtime.ps1 or overwrite other art/configs.

Final proof: build/hd-inventory-10mm-ammo/integration.json (exact installed hash,
fresh per-report totals, asset hashes and receipts). The final-* report folders
contain fresh SDL images. Earlier reports are retained as history and excluded
from final totals. asset-qa.json records alpha/crop and exact payload checks.
before-after.png compares original nearest x4 with selected HD at the same size.

The concurrent combat-crash-fix work completed before final tests/installation;
its current EXE is retained, not replaced with the older ammunition-only build.
Automated tests and frame review are not a complete gameplay walkthrough.
Launch: Start-Fallout-HD-World-Pilot.cmd. Restart after updating art or EXE.

Final result: 1272 PASS, 0 FAIL across 11 fresh reports on EXE
1B8D79B25C29B6E0FF1DA2E1501BFAE9F2DBE651924CA1ABBCA12182E6A97DFF
490 pre-existing art/config/save files checked. Art, saves and preference values
are unchanged; only the engine startup splash rotation counter advanced.
