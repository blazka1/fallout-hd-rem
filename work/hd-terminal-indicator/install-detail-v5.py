"""Validate, install and verify the isolated terminal detail patch."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,struct,shutil,argparse
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/generated/v13ent-terminal/detail-v5-20261114'
OLD=ROOT/'assets/hd/v13ent/terminal-user-contour-v3'
OUT=ROOT/'assets/hd/v13ent/terminal-detail-v5'
RUNTIME=ROOT/'runtime/hd-world-pilot';DATA=RUNTIME/'data/art/hd/world-pilot'
BACKUP=ROOT/'build/backups/before-terminal-detail-v5-20261114';REPORT=ROOT/'build/hd-terminal-indicator/detail-v5'
FILES=['asset-010.rgba','terminal-indicator-on.rgba','manifest.json']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def install():
 assert not BACKUP.exists(),'Existing backup: inspect before retry'
 assert sha(DATA/FILES[0])==sha(OLD/'terminal-off.rgba') and sha(DATA/FILES[1])==sha(OLD/'terminal-on.rgba')
 OUT.mkdir(exist_ok=True);states=[];arrays=[];mask=np.array(Image.open(SOURCE/'edit-mask.png').convert('RGB'))[:,:,0]
 for state in ['off','on']:
  name='terminal-'+state;im=Image.open(SOURCE/'exact'/(name+'.png')).convert('RGBA');a=np.array(im);b=np.array(Image.open(OLD/(name+'.png')).convert('RGBA'))
  assert a.shape==b.shape==(212,128,4) and np.array_equal(a[:,:,3],b[:,:,3])
  assert np.array_equal(a[53:76,92:112],b[53:76,92:112]) and np.array_equal(a[mask==0,:3],b[mask==0,:3])
  shutil.copy2(SOURCE/'exact'/(name+'.png'),OUT/(name+'.png'));raw=im.tobytes();(OUT/(name+'.rgba')).write_bytes(b'F1HD'+struct.pack('<IIII',1,128,212,4)+raw)
  arrays.append(a);states.append(dict(state=state,png_sha256=sha(OUT/(name+'.png')),rgba_sha256=sha(OUT/(name+'.rgba')),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest()))
 assert int(np.any(arrays[0]!=arrays[1],axis=2).sum())==62
 pack=dict(status='selected',native=[32,53],hd=[128,212],states=states,alpha_exact_previous=True,lamp_and_socket_exact_previous=True,protected_edge_rgb_exact_previous=True,state_difference_pixels=62,
    method='Local SeedVR2 detail restoration; shared body donor; original user matte and lamp/socket frozen in ComfyUI',source=str(SOURCE),seedvr2_prompt=read(SOURCE/'run.json')['prompt_id'],exact_alpha_prompt=read(SOURCE/'exact/run.json')['prompt_id'])
 save(OUT/'manifest.json',pack)
 files=set((RUNTIME/'data').rglob('*'));files.update((ROOT/'work/hd-world-pilot/fallout1-ce-main/src').rglob('*'));files.update(ROOT/p for p in ['runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/fallout.cfg','AGENTS.md','HD-TEXTURE-GUIDE.md'])
 base={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file()};BACKUP.mkdir(parents=True);save(BACKUP/'baseline.json',base)
 for name in FILES:shutil.copy2(DATA/name,BACKUP/name)
 for name in ['README.txt'] :shutil.copy2(Path(__file__).parent/name,BACKUP/name)
 shutil.copy2(ROOT/'build/hd-terminal-indicator/integration.json',BACKUP/'terminal-integration.json')
 m=read(DATA/'manifest.json');row=next(r for r in m['assets'] if r['asset_id']==10)
 shutil.copy2(OUT/'terminal-off.rgba',DATA/FILES[0]);shutil.copy2(OUT/'terminal-on.rgba',DATA/FILES[1])
 row.update(source_png=str(OUT/'terminal-off.png'),source_png_sha256=states[0]['png_sha256'],runtime_file_sha256=states[0]['rgba_sha256'],decoded_rgba_sha256=states[0]['decoded_rgba_sha256'])
 m['component_patches'].append(dict(component='terminal-detail-v5',package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),supersedes_terminal_package=str(OLD),animated_companion_file=FILES[1],animated_companion_sha256=states[1]['rgba_sha256'],alpha_and_lamp_preserved=True))
 save(DATA/'manifest.json',m);print('Installed 2 terminal images; exact old alpha, edge and lamp. EXE unchanged.')
def finish():
 base=read(BACKUP/'baseline.json');changed=[p for p,h in base.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
 allowed=[(DATA/n).relative_to(ROOT).as_posix() for n in FILES]
 # automap_exit() deletes this transient database when the open game closes.
 # The baseline was captured while the user's game was still running.
 transient='runtime/hd-world-pilot/data/MAPS/AUTOMAP.DB'
 lifecycle=[p for p in changed if p==transient and not (ROOT/p).exists()]
 assert sorted(p for p in changed if p not in lifecycle)==sorted(allowed),changed
 pack=read(OUT/'manifest.json');assert sha(DATA/FILES[0])==pack['states'][0]['rgba_sha256'] and sha(DATA/FILES[1])==pack['states'][1]['rgba_sha256']
 tests=[]
 for name in ['terminal','world']:
  m=read(REPORT/name/'manifest.json');assert m['exit_code']==0 and m['result']['failed']==0 and m['executable_sha256'].lower()==sha(RUNTIME/'fallout-ce.exe')
  assert m['base_sha256'].lower()==sha(DATA/FILES[0]) and m['companion_sha256'].lower()==sha(DATA/FILES[1])
  tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(REPORT/name/'manifest.json')))
 prev=ROOT/'build/hd-vault-materials-v2'
 assert np.array_equal(np.array(Image.open(prev/'world/entrance-classic.png')),np.array(Image.open(REPORT/'world/entrance-classic.png')))
 a=np.array(Image.open(prev/'terminal/terminal-on.png'));b=np.array(Image.open(REPORT/'terminal/terminal-on.png'));y,x=np.where(np.any(a!=b,axis=2))
 assert len(x)>100 and x.min()>=660 and x.max()<724 and y.min()>=300 and y.max()<406
 report=dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',package=str(OUT),backup=str(BACKUP),runtime=str(RUNTIME),launcher='Start-Fallout-HD-World-Pilot.cmd',executable_sha256=sha(RUNTIME/'fallout-ce.exe'),tests=tests,total_passed=sum(t['passed'] for t in tests),total_failed=0,
   alpha_edge_and_lamp_exact_previous=True,classic_frame_exact=True,render_changed_pixels=int(len(x)),render_changed_bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],protected_files_unchanged=len(base)-len(changed),runtime_changes=allowed,normal_game_exit_removed_transient_files=lifecycle,executable_source_menu_gameplay_and_vault_materials_unchanged=True)
 save(REPORT/'integration.json',report);save(ROOT/'build/hd-terminal-indicator/integration.json',report)
 note='''ТЕРМИНАЛ V5 — ЧЁТКОСТЬ И ДЕТАЛИ, 14 НОЯБРЯ 2026

Установлено assets/hd/v13ent/terminal-detail-v5/: корпус, кнопки и экран
восстановлены локальным SeedVR2 через ComfyUI, 512x848 -> 128x212.
Точная прежняя альфа V3, внешняя полоса RGB в 2 HD-пикселя, зелёная
лампочка и её гнездо сохранены попиксельно. Между состояниями 62 пикселя,
ритм 500/1100 мс не изменён. Один общий донор корпуса для обоих состояний.
SeedVR2 и упаковка не меняли EXE или исходники. Все 25 новых изображений
убежища из vault-materials-v2 сохранены; историческую раму V4 не ставить
поверх новой рамы из этого пакета. Нового ореола/прозрачности нет.
Квитанция: build/hd-terminal-indicator/detail-v5/integration.json.
Графы: assets/generated/v13ent-terminal/detail-v5-20261114/ и exact/.
Проверки установленного EXE: terminal 27 + world 319 = 346 PASS, 0 FAIL.
Классический кадр точный. Проходимость, меню, мир и конфиги сохранены.
Запуск: Start-Fallout-HD-World-Pilot.cmd, после замены перезапустить.

ИСТОРИЯ ПРЕДЫДУЩИХ ЭТАПОВ (НИЖЕ НЕ ТЕКУЩАЯ РАМА/ТЕРМИНАЛ)

'''
 readme=Path(__file__).parent/'README.txt';old=readme.read_text(encoding='utf-8');assert not old.startswith('ТЕРМИНАЛ V5');readme.write_text(note+old,encoding='utf-8');(OUT/'README.txt').write_text(note.split('ИСТОРИЯ')[0],encoding='utf-8')
 print(json.dumps(dict(installed=True,passed=report['total_passed'],failed=0,protected=report['protected_files_unchanged'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['install','finish']);a=p.parse_args();globals()[a.action]()
