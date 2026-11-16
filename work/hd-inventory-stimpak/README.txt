Stimpak PID40 — HD icon, 2026-11-14
Original inventory FID 0x07000073, art/inven/stimx.frm, 89x61 -> 356x244.
Original world FID 15; world sprite is not replaced.
Independent local SeedVR2 and Qwen Image 2.1 candidates are preserved in
assets/generated/inventory-stimpak/20261114/stimpak/ with source metadata,
original FRM/palette/prototype, workflow/API, prompts, run/history and hashes.
Selected Qwen for coherent metal, glass, gauge and preserved needle/hose.
Seed is retained for comparison; its red barrel and hose look too smooth.
ComfyUI removed alpha<=8 background noise and cropped (30,98,1088,746),
then scaled to 356x244. Every cleaned master pixel fits in the crop.
Soft alpha retained; dark/light backgrounds reviewed. F1HD payload exactly
matches the selected PNG. No palette reduction or small FRM replacement.

Engine changes: hd_hud.cc adds sixth registered item; hd_hud_test.cc and
inventoryHdTest in inventry.cc add PID40 and non-weapon test mapping.
Existing mechanics, healing code, prototypes and saves are not changed.
Scripts: work/hd-inventory-stimpak/20261114/{ammo.py,select.py}; task-local
filenames inherited from ammunition tooling. test.ps1 supports all six items.
install.ps1 validates loaded test, EXE/asset hashes and F1HD then backs up
and installs only the pilot EXE and stimpak.rgba. regression.ps1 checks five
previous items, cave and menu. Never run the historical prepare-runtime.ps1.
Final installation proof: build/hd-inventory-stimpak/integration.json.
Automated rendering checks and image review are not a full gameplay test.
Launch: Start-Fallout-HD-World-Pilot.cmd. Restart after updating files.
