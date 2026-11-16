from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,difflib,struct
from PIL import Image
import numpy as np
r=Path(__file__).resolve().parents[3];out=r/'build/hd-inventory-flare';runtime=r/'runtime/hd-world-pilot'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exe_hash=sha(runtime/'fallout-ce.exe');assert exe_hash==sha(r/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
reports=[]
names=[key+'-'+mode for key in ['unlit','lit'] for mode in ['loaded','missing','corrupt']]+['installed-'+str(pid) for pid in [79,4,8,21,29,30,40]]
paths=[out/'preview'/name/'manifest.json' for name in names]+[out/'world-regression/manifest.json',out/'menu-regression/manifest.json']
for p in paths:
 m=read(p);assert m['executable_sha256'].upper()==exe_hash
 result=m.get('result',m);assert result['failed']==0 and result['passed']>0 and m.get('exit_code',0)==0
 reports.append(dict(path=str(p.relative_to(r)),passed=result['passed'],failed=0,sha256=sha(p)))
assets=[]
for key,pid,size in [('unlit',79,(368,232)),('lit',205,(320,236))]:
 pack=r/f'assets/hd/inventory/flare-{key}/v1';im=Image.open(pack/'flare-hd-x4.png');data=(pack/'flare.rgba').read_bytes()
 assert im.mode=='RGBA' and im.size==size and data==struct.pack('<4sIIII',b'F1HD',1,*size,4)+im.tobytes()
 assert sha(pack/'flare.rgba')==sha(runtime/f'data/art/hd/inventory/flare-{key}/flare.rgba')
 src=r/f'assets/generated/inventory-flare/20261114/{key}'
 assert np.array_equal(np.array(Image.open(src/'seed/candidate.png'))[:,:,3],np.array(Image.open(src/'seed/lanczos.png'))[:,:,3])
 assets.append(dict(pid=pid,state=key,hd_size=size,asset_sha256=sha(pack/'flare.rgba'),png_payload_exact=True))
 m=read(pack/'manifest.json');m['status']='installed_and_verified';m['integration_report']='build/hd-inventory-flare/integration.json';m['files']={p.name:sha(p) for p in pack.iterdir() if p.is_file() and p.name!='manifest.json'};write(pack/'manifest.json',m)
protected=read(out/'protected-art-before.json');assert all(sha(runtime/name)==digest.upper() for name,digest in protected.items())
summary=dict(status='installed_and_verified',created_utc=datetime.now(timezone.utc).isoformat(),assets=assets,executable_sha256=exe_hash,protected_art_files_unchanged=len(protected),checks=reports,passed=sum(x['passed'] for x in reports),failed=0,receipts=[str(p.relative_to(r)) for p in (out/'installations').glob('*.json')],visual_review='Original/Seed/Qwen, dark/light alpha and SDL HUD/inventory/hand/drag captures reviewed. Lit v2 uses the unlit Qwen x4 candidate as second material reference; lit v1 is rejected and excluded.',ignition='Actual protinst_use_item on the same temporary object: PID79 -> PID205, inventory FID switches, light radius8 intensity65536 and EVENT_TYPE_FLARE scheduled. HUD switches and clears old HD metadata. Fixture and timer removed after test.',limitations='Inventory icons only; original world sprite and mechanics unchanged. No full burn-duration, gameplay or save/load walkthrough.')
write(out/'integration.json',summary);write(r/'work/hd-inventory-flare/task.json',summary)
patch=[]
for name in ['hd_hud.cc','hd_hud_test.cc','inventry.cc']:
 old=r/'build/backups/before-hd-flare-source-20261114'/name;new=r/'work/hd-world-pilot/fallout1-ce-main/src/game'/name
 patch+=list(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(r/'work/hd-inventory-flare/source.patch').write_text(''.join(patch))
print(json.dumps(dict(passed=summary['passed'],failed=0,executable_sha256=exe_hash)))
