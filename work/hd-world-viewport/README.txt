Fallout CE: full-height world beside the HUD

Component: render the world in the formerly black areas on both sides of the
centered 640x100 logical-pixel interface. The camera center and save-thumbnail
crop stay above the HUD. GNW keeps the panel and other windows over the map;
world input uses the visible window at the pointer. Incremental scrolling copies
the complete map buffer, including the new lower regions and their HD metadata.

Source tree: work/hd-world-pilot/fallout1-ce-main
Modified production files: game/map.cc, tile.cc/.h, gmouse.cc, actions.cc,
loadsave.cc, plus plib/gnw/gnw.cc (hidden windows do not intercept map input).
Regression coverage is in game/hd_world_pilot_test.cc.
No texture generation or original DAT/MAP edits.

Setting: [remaster] full_height_world=1, enabled by default. Setting it to 0
restores the old viewport after restart. Logical widths of 640 retain the old
380-pixel map at 640x480, since the HUD already fills the bottom width.

Backup: build/backups/before-full-height-world-20261114
Test runner: work/hd-world-viewport/test.ps1. It uses a separate test runtime and
copies current installed artwork without changing the live runtime's configs.
Choose a new output directory on each run, close Fallout before testing.

Example from project root:
  .\work\hd-world-pilot\tools\build.ps1 -Jobs 6
  .\work\hd-world-viewport\test.ps1 -Mode world -OutputDirectory build/hd-world-viewport/world-v1
  .\work\hd-world-viewport\test.ps1 -Mode viewport -Width 3440 -Height 1440 -OutputDirectory build/hd-world-viewport/ultrawide-v1

This note describes the implementation. Completion and installation are recorded
separately in build/hd-world-viewport/integration.json after fresh validation.
