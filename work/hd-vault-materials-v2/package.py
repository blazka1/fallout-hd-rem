"""Install only visually reviewed material assets; preserve all game/source files."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,struct,shutil,argparse
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'assets/generated/v13ent-vault/materials-v2-20261114'
OUT=ROOT/'assets/hd/v13ent/vault-materials-v2'
RUNTIME=ROOT/'runtime/hd-world-pilot'
DATA=RUNTIME/'data/art/hd/world-pilot'
REPORT=ROOT/'build/hd-vault-materials-v2'
BACKUP=ROOT/'build/backups/before-vault-materials-v2-20261114'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def package():
 OUT.mkdir(parents=True,exist_ok=True);rows={r['asset_id']:r for r in read(DATA/'manifest.json')['assets']};entries=[]
 for kind in ['walls','frame','door','floor']:
  for spec in read(RUN/kind/'prepared/specs.json'):
   i=spec['id'];src=RUN/kind/f'prepared/asset-{i:03}.png'
   if kind=='frame':src=RUN/'frame/refined-v2/asset-016.png'
   if kind=='floor':src=RUN/'floor/clean-v2/asset-088.png'
   im=Image.open(src).convert('RGBA');a=np.array(im)
   old=np.array(Image.open(spec['alpha']).convert('RGBA'))
   assert a.shape==old.shape and np.array_equal(a[:,:,3],old[:,:,3])
   assert np.array_equal(a[:,:,3],np.repeat(np.repeat(a[::4,::4,3],4,0),4,1))
   assert np.unique(a[:,:,3]).tolist()==[0,255]
   name=f'asset-{i:03}';shutil.copy2(src,OUT/(name+'.png'))
   raw=im.tobytes();(OUT/(name+'.rgba')).write_bytes(b'F1HD'+struct.pack('<IIII',1,im.width,im.height,4)+raw)
   entries.append(dict(asset_id=i,kind=kind,resource=rows[i]['original_resource'],prepared_source=str(src),png=str(OUT/(name+'.png')),png_sha256=sha(OUT/(name+'.png')),rgba_sha256=sha(OUT/(name+'.rgba')),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest(),previous_rgba_sha256=sha(DATA/(name+'.rgba')),alpha_exact_previous=True))
 assert len(entries)==25
 save(OUT/'manifest.json',dict(status='selected',runtime_verification_report=str(REPORT/'integration.json'),assets=entries,artwork='Local Qwen Image 2.1, Comfy registered crops and original/current alpha; clean interior and rusty exterior',
   qwen_runs={k:read(RUN/k/'run.json')['prompt_id'] for k in ['walls','frame','door']},seedvr2_refinement=read(RUN/'frame/refined-v2/run.json')['prompt_id'],grate_color_cleanup=read(RUN/'floor/clean-v2/run.json')['prompt_id'],rejected_floor_qwen_candidate=str(RUN/'floor/raw.png'),terminal_rgba_unchanged=True,requires_existing_recess_renderer=True))
 print('Packaged',len(entries),'images with exact previous alpha')
def install():
 assert not BACKUP.exists(),'Inspect existing backup before reinstall'
 m=read(DATA/'manifest.json');pack=read(OUT/'manifest.json');rows={r['asset_id']:r for r in m['assets']}
 for a in pack['assets']:assert sha(DATA/f"asset-{a['asset_id']:03}.rgba")==a['previous_rgba_sha256']
 files=set((RUNTIME/'data').rglob('*'));files.update((ROOT/'work/hd-world-pilot/fallout1-ce-main/src').rglob('*'))
 files.update(ROOT/p for p in ['runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/fallout.cfg','AGENTS.md','HD-TEXTURE-GUIDE.md'])
 baseline={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file()}
 BACKUP.mkdir(parents=True);save(BACKUP/'baseline.json',baseline)
 names=['manifest.json']+[f"asset-{a['asset_id']:03}.rgba" for a in pack['assets']]
 for name in names:shutil.copy2(DATA/name,BACKUP/name)
 for a in pack['assets']:
  name=f"asset-{a['asset_id']:03}.rgba";shutil.copy2(OUT/name,DATA/name)
  rows[a['asset_id']].update(source_png=a['png'],source_png_sha256=a['png_sha256'],runtime_file_sha256=a['rgba_sha256'],decoded_rgba_sha256=a['decoded_rgba_sha256'])
 m['component_patches'].append(dict(component='vault-materials-v2',package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),asset_ids=[a['asset_id'] for a in pack['assets']],preserves_terminal_and_recess=True))
 save(DATA/'manifest.json',m);print('Installed material images only; EXE untouched')
def finish():
 REPORT.mkdir(exist_ok=True);base=read(BACKUP/'baseline.json');pack=read(OUT/'manifest.json')
 for a in pack['assets']:assert sha(DATA/f"asset-{a['asset_id']:03}.rgba")==a['rgba_sha256']
 temporal=read(REPORT/'review/temporal-check.json');assert temporal['frames']==15 and not temporal['mismatches']
 changed=[p for p,h in base.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
 expected=[(DATA/n).relative_to(ROOT).as_posix() for n in ['manifest.json']+[f"asset-{a['asset_id']:03}.rgba" for a in pack['assets']]]
 assert sorted(changed)==sorted(expected),changed
 tests=[]
 for name in ['terminal','world']:
  m=read(REPORT/name/'manifest.json');assert m['exit_code']==0 and m['result']['failed']==0 and m['executable_sha256'].lower()==sha(RUNTIME/'fallout-ce.exe')
  tests.append(dict(name=name,passed=m['result']['passed'],failed=0,path=str(REPORT/name/'manifest.json')))
 old=ROOT/'build/hd-terminal-indicator/halo-v4/world/entrance-classic.png'
 assert np.array_equal(np.array(Image.open(old)),np.array(Image.open(REPORT/'world/entrance-classic.png')))
 save(REPORT/'integration.json',dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',package=str(OUT),backup=str(BACKUP),tests=tests,total_passed=sum(t['passed'] for t in tests),total_failed=0,
  executable_sha256=sha(RUNTIME/'fallout-ce.exe'),executable_and_source_unchanged=True,terminal_lamp_and_alpha_unchanged=True,classic_frame_exact=True,protected_unchanged=len(base)-len(changed),runtime_files_changed=changed,
  scope='25 images: 8 clean interior walls, 1 clean grate tile, rusty exterior frame and all 15 animated door frames. No gameplay/UI modifications.',launcher='Start-Fallout-HD-World-Pilot.cmd'))
 print('Verified',sum(t['passed'] for t in tests),'checks; all protected files unchanged')
 note='''МАТЕРИАЛЫ УБЕЖИЩА V2 — УСТАНОВЛЕНО И ПРОВЕРЕНО

Внутри: 8 стен ID152..159 и решётка ID88 — чистый серо-зелёный металл.
Снаружи: рама ID16 и 15 кадров двери ID160..174 сохраняют ржавчину.
Локальный Qwen Image 2.1 INT8; геометрия, альфа и регистрация сохранены.
Неподвижная часть всех кадров двери имеет общий RGB из кадра0.
Рама: выбран frame/refined-v2/asset-016.png, а не первые варианты.
Её нижний левый участок восстановлен SeedVR2 с сохранением кабеля и
устранённого в V4 выреза. Чёрные области нового Qwen-донорa исключены.
Пол: выбран floor/clean-v2, техническая нейтрализация рыжего оттенка и
умеренное повышение резкости. Кандидат Qwen изменил рисунок и отклонён.
Терминал и его лампа, EXE и исходники, меню и игровые данные не менялись.
Классический кадр совпадает попиксельно с предыдущей сборкой.

Ассеты: assets/hd/v13ent/vault-materials-v2/.
Графы и сырьё: assets/generated/v13ent-vault/materials-v2-20261114/.
Квитанция: build/hd-vault-materials-v2/integration.json.
Запуск: Start-Fallout-HD-World-Pilot.cmd. После установки перезапустить.
AGENTS.md в этой задаче не обновлялся.
'''
 (ROOT/'work/hd-vault-materials-v2/README.txt').write_text(note,encoding='utf-8');(OUT/'README.txt').write_text(note,encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['package','install','finish']);a=p.parse_args();globals()[a.action]()
