"""Validate evidence and protected files before installing the tested EXE."""
from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,shutil
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-terminal-indicator'
BACKUP=ROOT/'build/backups/before-terminal-indicator-20261114'
RUNTIME=ROOT/'runtime/hd-world-pilot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exe=RUNTIME/'fallout-terminal-test.exe'
digest=sha(exe)
assert digest==sha(ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
assert read(ROOT/'build/hd-world-pilot/logs/build-manifest.json')['executable_sha256'].lower()==digest
baseline=read(BACKUP/'baseline.json')
allowed=[
 'work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.cc',
 'work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.h',
 'work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot_test.cc',
 'runtime/hd-world-pilot/data/art/hd/world-pilot/asset-010.rgba',
 'runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json']
changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
assert sorted(changed)==sorted(allowed),changed
tests=[]
for name in ['loaded-v1','missing-v1','corrupt-v1','mismatched-v1','world-v1','hud-v1','menu-v1','benchmark-v1']:
 m=read(OUT/name/'manifest.json');assert m['executable_sha256'].lower()==digest
 assert m['exit_code']==0 and m['result']['failed']==0 and m['result']['passed']>0
 assert m['base_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/asset-010.rgba')
 assert m['companion_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/terminal-indicator-on.rgba')
 tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(OUT/name/'manifest.json')))
before=np.array(Image.open(OUT/'baseline/entrance-hd.png').convert('RGBA'))
after=np.array(Image.open(OUT/'world-v1/entrance-hd.png').convert('RGBA'))
y,x=np.where(np.any(before!=after,axis=2))
assert len(x)>0 and x.min()>=660 and x.max()<724 and y.min()>=294 and y.max()<400
assert np.array_equal(np.array(Image.open(OUT/'baseline/entrance-classic.png')),np.array(Image.open(OUT/'world-v1/entrance-classic.png')))
comparison=dict(hd_changes_only_inside_terminal=True,hd_changed_pixels=len(x),hd_difference_bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],classic_frame_pixel_exact=True,protected_unchanged_before_install=len(baseline)-len(changed),intentional_changes=changed)
save(OUT/'review/frame-and-file-comparison.json',comparison)
timings=[]
b=read(OUT/'benchmark-before-v2/benchmark.json');a=read(OUT/'benchmark-v1/benchmark.json')
for old,new in zip(b['rows'],a['rows']):
 assert (old['requested_width'],old['mode'],old['workload'])==(new['requested_width'],new['mode'],new['workload'])
 if old['mode']=='hd_enabled':timings.append(dict(width=old['requested_width'],workload=old['workload'],before_ms=old['median_ms'],after_ms=new['median_ms']))
shutil.copy2(exe,RUNTIME/'fallout-ce.exe')
assert sha(RUNTIME/'fallout-ce.exe')==digest
report=dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',executable_sha256=digest,previous_executable_sha256=baseline['runtime/hd-world-pilot/fallout-ce.exe'],backup=str(BACKUP),selected_component=str(ROOT/'assets/hd/v13ent/terminal-indicator-v1'),runtime=str(RUNTIME),launcher='Start-Fallout-HD-World-Pilot.cmd',tests=tests,total_passed=sum(t['passed'] for t in tests),total_failed=0,comparison=comparison,performance=dict(scope='24-sample sequential hidden SDL benchmarks, not gameplay FPS; benchmark holds lamp off; real clock separately tested',rows=timings),unchanged='Original DAT/MAP/FRM, gameplay/collision, menu and inventory artwork/code, other 205 world images, settings and saves',runtime_files_changed=['fallout-ce.exe','data/art/hd/world-pilot/asset-010.rgba','data/art/hd/world-pilot/manifest.json'],runtime_files_added=['data/art/hd/world-pilot/terminal-indicator-on.rgba'],qwen_prompt_id='583d2a80-1582-45a1-aa97-38d0da6b96ed',comfy_preparation_prompt_id='f2cba50c-7972-4288-981b-d473191db3f7')
save(OUT/'integration.json',report)
print(json.dumps(dict(installed=True,sha256=digest,passed=report['total_passed'],failed=0,other_protected_files_unchanged=len(baseline)-len(changed)-1)))
