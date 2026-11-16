Component: Fallout 1.0 combat message compatibility (2026-11-14)

Diagnosis: original English MASTER.DAT combat.msg has 513 = "%s %s hit for
%d hit points", but this CE calls snprintf(name, damage). Damage is read as
an address for the second %s. The Windows crash dump has 0xc0000005 at
fallout-ce.exe+0x5046a1 in strnlen, with the low 32 bits of the string pointer
set to 2. The stack contains combat_display_hit and combat_anim_finished.
The same unsafe formatting exists for critical/aimed hits and low damage.
CE also expects male/female message groups and misc IDs absent in 1.0.

Fix: combat_message_compat.cc normalizes this legacy table in memory at
combat_init, using its original words, verbs and critical descriptions.
It creates player/male/female templates and required misc/flag IDs. A full
replacement table is prepared before committing. Modern layouts with ID100
are unchanged. DAT/MSG files, damage rules, animation, saves, textures and
configs are not patched by this component.

Production edits: combat.cc (initialization call), new combat_message_compat
.cc/.h, message.cc/.h (expose existing copying message_add API), CMakeLists.txt.
Regression harness: hd_world_pilot_test.cc, enabled only inside the existing
isolated preview path with FALLOUT_COMBAT_TEST. Normal gameplay has no test
hooks enabled. The animated test heals the test player and forces damage
for a final test kill; these settings are confined to the unsaved test map.

Runner: work/combat-crash-fix/test.ps1 -Mode combat|world|menu
Use a fresh OutputDirectory. Tests run in build/combat-crash-fix/test-runtime.
One Fallout process at a time, including other component test executables.
MSVC FileTracker and SDL startup require the authorized external-sandbox
execution path on this machine. Keep all preview env vars process-local.

Baseline: build/combat-crash-fix/baseline-repro-unsandboxed/manifest.json
Crash reproduced after original cave/rat checks; exit -1073741819 (c0000005).
Fixed: fixed-v1 (77 PASS), world-regression (319 PASS), menu-regression.
Fixed-v1 manifest says mode=world because the runner gained a separate
combat mode afterwards; its checks.txt identifies the combat cases.
Current installation status/hashes are in build/combat-crash-fix/integration.json.
Backup: build/backups/before-combat-crash-20261114 (original EXE and edited sources).
AGENTS.md is intentionally unchanged.
