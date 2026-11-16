Main menu, original-inspired layout — 2026-11-14

Installed in runtime/hd-world-pilot. Use Start-Fallout-HD-World-Pilot.cmd.
Selected background: assets/hd/main-menu/background-seed-qwen-v2/background-4k.png.
Runtime: data/art/hd/main-menu/menu-background-v2.bmp, lossless RGB conversion.
The selected SeedVR2 -> Qwen helmet is preserved; Qwen extends the ruined city
to the right. A96px cross-blend joins the extension, without a darkening layer.
Generation graphs and raw outputs: assets/generated/main-menu/original-layout-20261114.

Code: isolated game/hd_mainmenu.cc. Accepts5:6 and16:9 assets, draws at original
exposure with proportional cover scaling, and places compact buttons upper-right.
Original order: Intro/New Game/Load Game/Credits/Exit. Existing button artwork and
labels retained for later work; title, footer, hints and dark overlays removed.
game/main.cc changes only the test expectation for Tab after the reordered Intro.

Validation:139 menu checks, fresh frames at640x480/1080p/1440p/4K/ultrawide/4:3,
and exact4K background pixel comparison outside buttons (no tint or overlay).
Reports: build/hd-menu-original-layout/preview-v3 and integration.json.
preview-v1 exercised the old EXE; preview-v2 retained an old keyboard-test
expectation. Neither is the final installed result. Use preview-v3.
Backup: build/backups/before-original-layout-menu-20261114.
Other textures, gameplay, saves/config and separate classic/hd-menu runtimes
were not changed. AGENTS.md was not updated.
