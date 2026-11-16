10mm Pistol HD v2 — 14 November 2026

User-selected current HD design enriched with details from the new mirrored reference, followed by extremely slight rust.
Source master: assets/generated/inventory-10mm-pistol/qwen21-subtle-rust-v7-20261114/pistol-subtle-rust.png (768x768).
Geometry and materials derive from the original installed v1 HD; detail transfer is recorded in qwen21-current-hd-details-v6-20261114.
User explicitly requested this latest variant for inventory/HUD/cursor.

PID8; inventory FID0x07000004; original art/inven/pistol.frm; native70x63.
Final pistol-hd-x4.png:280x252 RGBA; pistol-master.png:768x768 cleaned master.
ComfyUI deterministic postprocess: alpha<=15 noise removal, retain higher soft alpha, crop x49 y77 w670 h603 (10:9), Lanczos280x252.
The crop retains all nonzero pixels of the cleaned master. Old native layout and source density are retained closely; no aspect distortion.
F1HD header <4sIIII>:F1HD,1,280,252,4; total282260 bytes; payload equals decoded PNG RGBA exactly.
Original DAT FRM fallback unchanged. No new loose FRM.

Scope: replace runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba only.
The already installed EXE supports this item; no rebuild or executable update.
Previous pistol v1 remains in assets/hd/inventory/10mm-pistol/v1 and in the verified install backup.

Workflow, API graph and histories: generation directory; selected package includes generation and final postprocess graphs.
Generation result.json describes the earlier preview stage; installed status is in manifest.json and integration report.
Install/test receipt: build/hd-inventory-pistol/v2-20261114/integration.json.
Launch: Start-Fallout-HD-World-Pilot.cmd; restart game after updating assets.
