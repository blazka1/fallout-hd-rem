from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,difflib,struct
from PIL import Image
import numpy as np

r=Path(__file__).resolve().parents[3];out=r/'build/hd-inventory-stimpak';runtime=r/'runtime/hd-world-pilot';pack=r/'assets/hd/inventory/stimpak/v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exe_hash=sha(runtime/'fallout-ce.exe');assert exe_hash==sha(r/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
reports=[]
paths=[out/'preview'/name/'manifest.json' for name in ['loaded','missing','corrupt','item-4','item-8','item-21','item-29','item-30']]+[out/'world-regression/manifest.json',out/'menu-regression/manifest.json']
for p in paths:
 m=read(p);assert m['executable_sha256'].upper()==exe_hash
 result=m.get('result',m);assert result['failed']==0 and result['passed']>0
 assert m.get('exit_code',0)==0
 reports.append(dict(path=str(p.relative_to(r)),passed=result['passed'],failed=0,sha256=sha(p)))
im=Image.open(pack/'stimpak-hd-x4.png');data=(pack/'stimpak.rgba').read_bytes()
assert im.mode=='RGBA' and im.size==(356,244) and data==struct.pack('<4sIIII',b'F1HD',1,356,244,4)+im.tobytes()
assert sha(pack/'stimpak.rgba')==sha(runtime/'data/art/hd/inventory/stimpak/stimpak.rgba')
src=r/'assets/generated/inventory-stimpak/20261114/stimpak'
assert np.array_equal(np.array(Image.open(src/'seed/candidate.png'))[:,:,3],np.array(Image.open(src/'seed/lanczos.png'))[:,:,3])
protected=read(out/'protected-art-before.json');assert all(sha(runtime/name)==digest.upper() for name,digest in protected.items())
summary=dict(status='installed_and_verified',created_utc=datetime.now(timezone.utc).isoformat(),pid=40,inventory_fid='0x07000073',native_size=[89,61],hd_size=[356,244],executable_sha256=exe_hash,asset_sha256=sha(pack/'stimpak.rgba'),png_payload_exact=True,seed_alpha_matches_baseline=True,protected_art_files_unchanged=len(protected),checks=reports,passed=sum(x['passed'] for x in reports),failed=0,receipts=[str(p.relative_to(r)) for p in (out/'installations').glob('*.json')],visual_review='Original, Seed and Qwen compared. Dark/light alpha and fresh SDL inventory, hand, HUD and drag frames reviewed at 1080p/4K. Needle and hose intact; loop transparent.',limitations='Automated render checks and visual review, not a full gameplay walkthrough or a new healing-mechanics test.')
write(out/'integration.json',summary);write(r/'work/hd-inventory-stimpak/task.json',summary)
m=read(pack/'manifest.json');m['status']='installed_and_verified';m['integration_report']='build/hd-inventory-stimpak/integration.json';m['selection']='Qwen: coherent glass and metal, legible gauge, intact needle and hose. Seed rejected for overly smooth red barrel and hose.';m['files']={p.name:sha(p) for p in pack.iterdir() if p.is_file() and p.name!='manifest.json'};write(pack/'manifest.json',m)
patch=[]
for name in ['hd_hud.cc','hd_hud_test.cc','inventry.cc']:
 old=r/'build/backups/before-hd-stimpak-source-20261114'/name;new=r/'work/hd-world-pilot/fallout1-ce-main/src/game'/name
 patch+=list(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(r/'work/hd-inventory-stimpak/source.patch').write_text(''.join(patch))
print(json.dumps(dict(passed=summary['passed'],failed=0,executable_sha256=exe_hash)))
