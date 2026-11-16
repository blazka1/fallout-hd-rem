Flare: unlit PID79 and lit PID205, 2026-11-14
Inventory FIDs 0x0700003B (flare.frm,92x58) and 0x0700007B (flareon.frm,80x59).
HD targets 368x232 and 320x236. Both world FIDs are46 and remain original.
Local SeedVR2 is an independent original-reference baseline for each state.
Qwen unlit uses the unlit original. Qwen lit uses the lit original for framing
and flame plus the finished unlit master as a second material/body reference.
All originals, workflows, prompts, run IDs, history and candidates are retained
under assets/generated/inventory-flare/20261114/{unlit,lit}.
Selected packages: assets/hd/inventory/flare-{unlit,lit}/v1.
Python orchestrates ComfyUI and performs packing/QA; artistic generation and
final alpha/crop/scale are ComfyUI nodes. F1HD is exact selected RGBA PNG bytes.

Engine: hd_hud.cc registers both states, now eight items total. Test PID/FID
mappings extended in hd_hud_test.cc and inventoryHdTest in inventry.cc.
Flare remains a throwable weapon with the original use action and mechanics.
Actual ignition test calls protinst_use_item on a temporary real flare,
checks same-object PID/FID switch, light radius8/intensity65536, burn queue,
HUD redraw and old HD metadata removal, then removes its timer and fixture.
No changes to original use/lighting/timer code, prototypes, DAT or save format.
The renderer uses native dimensions per state; no assumption of equal canvases.

Scripts: 20261114/flare.py export/submit/collect, select.py prepare/collect/compare.
Existing run.json must be collected, not resubmitted. Use new paths for revisions.
Build with work/hd-world-pilot/tools/build.ps1. test.ps1 selects PID79 or205.
install.ps1 -ItemPid79|205 validates loaded tests, EXE and F1HD hashes, backs up
and installs only pilot EXE and the corresponding flare.rgba. regression.ps1
checks actual ignition with both assets present, all six previous items,
world and menu. Never run historical prepare-runtime.ps1.

Final installation evidence: build/hd-inventory-flare/integration.json.
Source backup: build/backups/before-hd-flare-source-20261114.
Launch Start-Fallout-HD-World-Pilot.cmd; restart after new EXE/art installation.
Automated render and ignition tests are not a full burn-duration or gameplay
walkthrough. World sprite and universal animation replacement are out of scope.

Selection: Qwen unlit and Qwen lit v2. Lit v1 rejected for coarse wrinkled
texture and enlarged framing. V2 uses the smaller unlit x4 candidate as
material reference, strict original lit framing and smooth-paper constraints.
Final alpha threshold8/255 retains soft edges. Crops unlit(6,106,1139,718),
lit(78,106,997,735); all cleaned master pixels retained.
