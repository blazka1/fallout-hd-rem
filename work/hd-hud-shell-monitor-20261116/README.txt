HUD shell and log monitor — first review candidate, 16 November 2026

Original status: generated for visual review. The user then approved installation
and asked to correct Qwen's distorted SKILLDEX label. See installation below.

Source: art/intrface/iface.frm (640x100), original palette export from MASTER.DAT.
Original resources remain in assets/reference/hud-panel-audit-20261115.
Output: assets/generated/hud-shell-monitor/seed-qwen-v1-20261116.

1. Repeat-edge padding 2 pixels above/below the source; 640x104 canvas.
2. Local SeedVR2 3B INT8, x4, 2560x416, 1 Euler/simple step, CFG 1,
   seed 16112026. Result is the actual Qwen input, not a parallel variant.
3. Canny 0.25/0.65 from that result. The inspected control image is saved.
4. Local Qwen Image 2.1 INT8 + Qwen3VL 8B INT8 + Qwen VAE BF16,
   native Fun ControlNet Union INT8, strength 1 throughout; 25 Euler/simple
   steps, CFG 1, seed 16112026, denoise 1, CPU KV cache, tiled VAE decode.
   Exact prompt: output/qwen/prompt.txt (output is the directory above).
5. Remove the padding; scale 2560x400 to 3840x600. This is a x6 delivery
   master; generative working resolution is x4, not native x6 restoration.
6. ComfyUI mask composite retains original controls, counters, labels,
   weapon surface, AP lights, hatch and outermost boundary as context.
   Their exact regions are in review/protected-regions.json.
7. Transparent shell layer uses the same mask. Final exact-alpha packaging
   corrects a <=1/255 float quantization error in the Comfy mask conversion;
   generated RGB is preserved. This is packaging, not a painted replacement.

Review outputs:
  review/comparison-full.png — original / Seed / Seed->Qwen, same scale
  review/comparison-monitor.png — close-up of the monitor housing/glass
  review/shell-monitor-context.png — full 3840x600 preview with old controls
  review/monitor-candidate.png — 1254x600 crop of the left housing
  review/shell-monitor-layer-exact-alpha.png — shell/monitor layer, controls cut out
  review/validation.json — dimensions, protected-pixel check, file hashes

All workflow graphs, API prompts, prompt IDs, source hashes and execution
histories are saved alongside each stage. Canny guides geometry but does
not prove exact registration of every interior bevel; inspect the candidate.
This is an asset preview, not an in-engine render or an HD HUD implementation.

Use existing ComfyUI Python and existing local server. Commands:
  pipeline.py submit seed / collect seed
  pipeline.py submit control / collect control
  pipeline.py submit qwen / collect qwen
  review.py submit / collect / compare
Already-submitted jobs are never resubmitted automatically.

Installation stage — 16 November 2026

Selected package: assets/hd/hud-panel/seed-qwen-v1. The source Qwen file remains
untouched. package.py reuses a clean blue strip inside the nameplate and adds
the exact text SKILLDEX as deterministic UI typography; RGB outside the repair
box is unchanged. The base is made opaque and packaged losslessly in F1HD x6.

The current world-pilot source now supports this x6 opaque HUD asset alongside
the existing x4 HD icons, with a separate remaster/hd_hud_panel setting (default
1). Setting it to 0 before restarting restores the classic panel. Missing or
invalid assets also keep classic graphics; HD items remain independent.

The actual GNW interface buffer receives HD ownership metadata, so upper windows,
cursors, text and dynamic controls still occlude the panel normally. The log
restores HD glass before drawing original live text; glyph writes remove HD
ownership only where text has coverage. Original FRM cache bytes are retained.
Normal INV/options/MAP/CHA/PIP and red switch surfaces use registered crops of
the approved Qwen panel. Pressed states use the same material with reduced light.
Weapon surface, action text, HP/AC glyphs, AP lamps and open combat controls keep
their existing runtime drawing; they replace Qwen's baked example contents.
The closed combat hatch returns to the Qwen panel after opening/closing.
Opaque stationary panel cells use the world layer's cache; soft HD item cells
continue to recomposite with their captured background.

Verification runs and SDL captures: build/hd-hud-shell-install-20261116.
Baseline: the previously installed executable, current full world package.
Final: real HUD at 1080p and 4K, button press/return, log text, combat hatch,
window occlusion, cursor, inventory, HD item and renderer recreation checks.
Also: corrupt-panel fallback and the complete 139-check menu regression.
The integration report records exact results and installed EXE/asset hashes.

Only runtime/hd-world-pilot/fallout-ce.exe is replaced and
data/art/hd/hud-panel/shell-monitor.rgba is added. Configs, saves, maps, world
packages, rats, player, inventory icons and menu assets are preserved by hash.
Backup: build/backups/before-hd-hud-shell-20261116.
Launcher: Start-Fallout-HD-World-Pilot.cmd. Restart after installation.
No AGENTS.md edits were made.

Installed result: 359 PASS, 0 FAIL on the final EXE (110 HUD + 110 corrupt
fallback + 139 menu). Outside-HUD pixels match the previous EXE exactly at
1920x1080 and 3840x2160. Installer verified all 1390 other pre-existing runtime
files unchanged. EXE SHA256:
2029577319701b415d2d9547c760de64c181effcb1879132c9b568c21d4edeb2

Baseline harness note: CE resolves fallout.cfg beside argv[0]. The baseline
startup advanced the live splash counter once; the exact original bytes were
recovered and restored against the pre-task SHA256 before installation. Details
are in startup-counter-restoration.json. The harness now copies alternate EXEs
into staging before launch so that future baseline runs isolate config writes.
