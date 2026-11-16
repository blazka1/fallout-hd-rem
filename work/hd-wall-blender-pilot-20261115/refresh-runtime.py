"""Adopt the other chat's finished rat EXE without modifying shared files."""
from prepare import *
import numpy as np
def main():
 report=R/'build/hd-rat-world-integration-20261115/verified/world';m=read(report/'manifest.json');exe=sha(LIVE/'fallout-ce.exe')
 assert m['executable_sha256'].lower()==exe and m['result']['failed']==0
 # All integration/fallback runs must be complete before taking a snapshot.
 for name in ['player','rat','world','menu','hud','missing-frame','corrupt-frame','missing-aimed','corrupt-aimed']:
  check=read(report.parent/name/'manifest.json')
  assert check['result']['failed']==0 and check['executable_sha256'].lower()==exe,name
 rows=read(O/'placement-slices.json')['images']
 for row in rows:assert sha(LIVE/'data/art/hd/world-pilot'/row['file'])==row['before_sha256']
 assert not (W/'baseline-initial.json').exists(),'Refresh already performed'
 shutil.copy2(W/'baseline.json',W/'baseline-initial.json')
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=exe,adopted_rat_integration=True))
 dest=B/'before-final';dest.mkdir(exist_ok=True)
 matched=[]
 for p in (B/'before').glob('*.png'):
  if 'classic' not in p.name and p.name not in ['entrance-hd.png','cave-22662-hd.png']:continue
  q=report/p.name
  if not q.exists():continue
  assert np.array_equal(np.asarray(Image.open(p)),np.asarray(Image.open(q))),('Before capture changed',p.name)
  matched.append(p.name)
 for q in report.glob('*.png'):shutil.copy2(q,dest/q.name)
 for name in ['result.json','manifest.json','checks.txt']:shutil.copy2(report/name,dest/name)
 save(B/'runtime-refresh.json',dict(exe_sha256=exe,reference_report=str(report.relative_to(R)),pixel_identical_before_captures=len(matched),before_frames=matched,shared_runtime_modified=False))
 print('Refreshed isolated runtime from finished rat integration;',len(matched),'before captures pixel-identical')
if __name__=='__main__':main()
