"""Install only the tested soft-edge EXE after verifying protected files."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-terminal-indicator/natural-edge-v2'
BACKUP=ROOT/'build/backups/before-terminal-natural-edge-v2-20261114'
RUNTIME=ROOT/'runtime/hd-world-pilot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exe=RUNTIME/'fallout-terminal-test.exe';digest=sha(exe)
assert digest==sha(ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
assert read(ROOT/'build/hd-world-pilot/logs/build-manifest.json')['executable_sha256'].lower()==digest
baseline=read(BACKUP/'baseline.json')
allowed=['work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.cc','work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.h','work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot_test.cc','work/hd-world-pilot/fallout1-ce-main/src/game/object.cc','runtime/hd-world-pilot/data/art/hd/world-pilot/asset-010.rgba','runtime/hd-world-pilot/data/art/hd/world-pilot/terminal-indicator-on.rgba','runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json']
changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
assert sorted(changed)==sorted(allowed),changed
review=read(OUT/'pixel-review.json');review['changed_protected_files']=changed;save(OUT/'pixel-review.json',review)
tests=[]
for name in ['loaded','missing','corrupt','mismatched','world','hud','menu','benchmark']:
 m=read(OUT/'release'/name/'manifest.json')
 assert m['executable_sha256'].lower()==digest and m['exit_code']==0 and m['result']['failed']==0 and m['result']['passed']>0
 assert m['base_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/asset-010.rgba')
 assert m['companion_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/terminal-indicator-on.rgba')
 tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(OUT/'release'/name/'manifest.json')))
checks=(OUT/'release/loaded/checks.txt').read_text()
assert 'PASS removed outline reveals exact real background' in checks
assert '0 wrong)' in checks
before=np.array(Image.open(ROOT/'build/hd-terminal-indicator/loaded-v1/terminal-on.png').convert('RGBA'))
after=np.array(Image.open(OUT/'release/loaded/terminal-on.png').convert('RGBA'))
y,x=np.where(np.any(before!=after,axis=2));assert 0<len(x)<2000 and x.min()>=660 and x.max()<724 and y.min()>=294 and y.max()<400
assert np.array_equal(np.array(Image.open(ROOT/'build/hd-terminal-indicator/world-v1/entrance-classic.png')),np.array(Image.open(OUT/'release/world/entrance-classic.png')))
shutil.copy2(exe,RUNTIME/'fallout-ce.exe');assert sha(RUNTIME/'fallout-ce.exe')==digest
report=dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',executable_sha256=digest,previous_executable_sha256=baseline['runtime/hd-world-pilot/fallout-ce.exe'],backup=str(BACKUP),package=str(ROOT/'assets/hd/v13ent/terminal-natural-edge-v2'),runtime=str(RUNTIME),launcher='Start-Fallout-HD-World-Pilot.cmd',tests=tests,total_passed=sum(t['passed'] for t in tests),total_failed=0,pixel_review=read(OUT/'pixel-review.json'),real_background_exact=True,classic_frame_exact=True,lamp_and_blink_unchanged=True,protected_files_unchanged=len(baseline)-len(changed)-1,intentional_source_and_asset_changes=changed,scope='Only the single original V13ENT doorcomp terminal; native-texel background cache. Original DAT/MAP/FRM, gameplay, settings, other artwork unchanged.',comfy_prompt_id='61a5daff-b11c-4167-9140-079811347cd8',historical_attempts=['loaded/world/benchmark','optimized/loaded/benchmark','final/loaded/world/benchmark'],performance_report=str(OUT/'release/benchmark/benchmark.json'),performance_limit='24-sample hidden SDL CPU timing, not gameplay FPS; baseline comparisons are sequential and may include host load variation')
save(OUT/'integration.json',report)
current=ROOT/'build/hd-terminal-indicator/integration.json';history=ROOT/'build/hd-terminal-indicator/integration-v1.json'
if not history.exists():shutil.copy2(current,history)
save(current,report)
print(json.dumps(dict(installed=True,sha256=digest,passed=report['total_passed'],failed=0,unchanged=report['protected_files_unchanged'])))
