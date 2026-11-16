from pipeline import *
actual=ROOT/'work/hd-world-pilot/fallout1-ce-main/src'
tested=W/'test-source/src'
diffs=sorted(p.relative_to(actual).as_posix() for p in actual.rglob('*') if p.is_file() and (not (tested/p.relative_to(actual)).exists() or sha(p)!=sha(tested/p.relative_to(actual))))
assert diffs==['game/hd_wall_geometry_test.inc','game/hd_world_pilot_test.cc'],diffs
exe=B/'test-msvc/RelWithDebInfo/fallout-ce.exe'
assert exe.exists()
shutil.copy2(W/'test-exe.json',W/'test-exe-first.json')
save(W/'test-exe.json',dict(source_differences=diffs,exe_sha256=sha(exe),purpose='Diagnostics-only fixes for identical wall texture assertion and decoration visibility through translucent walls; no rendering/gameplay changes; never installed in live runtime'))
shutil.copy2(exe,RT/'fallout-ce.exe')
print('Verified only two diagnostic source differences; staged isolated test EXE',sha(exe))
