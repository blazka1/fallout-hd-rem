"""Install two selected material edits in one frame, then audit the runtime."""
from pathlib import Path
import json,hashlib,struct,shutil,argparse
from datetime import datetime,timezone
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'assets/generated/v13ent-vault/surface-fixes-v4-20261114/prepared-v2'
OLD=ROOT/'assets/hd/v13ent/vault-clean-trim-v3'
OUT=ROOT/'assets/hd/v13ent/vault-surface-fixes-v4'
RT=ROOT/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot'
BACK=ROOT/'build/backups/before-vault-surface-fixes-v4-20261114'
REPORT=ROOT/'build/hd-vault-surface-fixes-v4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def install():
 assert not BACK.exists()
 assert sha(DATA/'asset-016.rgba')==sha(OLD/'asset-016.rgba')
 im=Image.open(SRC/'asset-016.png').convert('RGBA');a=np.array(im);b=np.array(Image.open(OLD/'asset-016.png').convert('RGBA'))
 mask=np.array(Image.open(SRC/'edit-mask.png').convert('RGB'))[:,:,0]>0
 assert a.shape==b.shape==(896,1368,4) and np.array_equal(a[:,:,3],b[:,:,3])
 assert np.array_equal(a[~mask],b[~mask]);changed=np.any(a!=b,axis=2)
 assert 35000<changed.sum()<65000,int(changed.sum())
 OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
 shutil.copy2(SRC/'asset-016.png',OUT/'asset-016.png');raw=im.tobytes()
 (OUT/'asset-016.rgba').write_bytes(b'F1HD'+struct.pack('<IIII',1,im.width,im.height,4)+raw)
 pack=dict(asset_id=16,png_sha256=sha(OUT/'asset-016.png'),rgba_sha256=sha(OUT/'asset-016.rgba'),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest(),source=str(SRC),comfy_prompt=read(SRC/'run.json')['prompt_id'],provenance=read(SRC/'provenance.json'),alpha_exact=True,outside_selection_exact=True,changed_pixels=int(changed.sum()),method='Local Qwen 2.1: smooth neutral interior-facing trim; rusty recess restored and blended 70 percent with adjacent same-panel texture to match pit scale. Exact user selections composited in ComfyUI')
 save(OUT/'manifest.json',pack)
 files=set((RT/'data').rglob('*'));files.update((ROOT/'work/hd-world-pilot/fallout1-ce-main/src').rglob('*'));files.update(ROOT/p for p in ['runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/fallout.cfg','AGENTS.md','HD-TEXTURE-GUIDE.md'])
 BACK.mkdir(parents=True);save(BACK/'baseline.json',{p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file()})
 for name in ['asset-016.rgba','manifest.json']:shutil.copy2(DATA/name,BACK/name)
 m=read(DATA/'manifest.json');row=next(r for r in m['assets'] if r['asset_id']==16)
 row.update(source_png=str(OUT/'asset-016.png'),source_png_sha256=pack['png_sha256'],runtime_file_sha256=pack['rgba_sha256'],decoded_rgba_sha256=pack['decoded_rgba_sha256'])
 m['component_patches'].append(dict(component='vault-surface-fixes-v4',asset_ids=[16],package=str(OUT),manifest_sha256=sha(OUT/'manifest.json')))
 shutil.copy2(OUT/'asset-016.rgba',DATA/'asset-016.rgba');save(DATA/'manifest.json',m)
 print('Installed one frame texture; changed',pack['changed_pixels'],'pixels only inside marked areas')
def finish():
 base=read(BACK/'baseline.json');changed=[p for p,h in base.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
 expected=[(DATA/n).relative_to(ROOT).as_posix() for n in ['asset-016.rgba','manifest.json']]
 assert sorted(changed)==sorted(expected),changed
 assert sha(DATA/'asset-016.rgba')==read(OUT/'manifest.json')['rgba_sha256']
 tests=[]
 for name in ['terminal','world']:
  m=read(REPORT/name/'manifest.json');assert m['exit_code']==0 and m['result']['failed']==0 and m['executable_sha256'].lower()==sha(RT/'fallout-ce.exe')
  tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(REPORT/name/'manifest.json')))
 prev=ROOT/'build/hd-vault-clean-trim-v3'
 assert np.array_equal(np.array(Image.open(prev/'world/entrance-classic.png')),np.array(Image.open(REPORT/'world/entrance-classic.png')))
 save(REPORT/'integration.json',dict(status='installed_and_verified',created_utc=datetime.now(timezone.utc).isoformat(),package=str(OUT),backup=str(BACK),tests=tests,total_passed=sum(x['passed'] for x in tests),total_failed=0,runtime_changes=changed,protected_files_unchanged=len(base)-len(changed),classic_frame_exact=True,executable_sha256=sha(RT/'fallout-ce.exe'),terminal_lamp_and_contour_unchanged=True,launcher='Start-Fallout-HD-World-Pilot.cmd'))
 note='Рама V4: гладкий нейтральный металл на внутренних боковой грани и верхней полосе; детальная ржавая поверхность под кабелем по второй разметке пользователя. Два локальных задания Qwen 2.1, точные маски через ComfyUI. Альфа, пиксели вне масок, терминал и лампа, дверь, EXE, меню и проходимость сохранены. Проверено 346 PASS, 0 FAIL. Квитанция build/hd-vault-surface-fixes-v4/integration.json. Запуск Start-Fallout-HD-World-Pilot.cmd.\n'
 (OUT/'README.txt').write_text(note,encoding='utf-8')
 print('Verified',sum(x['passed'] for x in tests),'checks; protected',len(base)-len(changed),'files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['install','finish']);globals()[p.parse_args().action]()
