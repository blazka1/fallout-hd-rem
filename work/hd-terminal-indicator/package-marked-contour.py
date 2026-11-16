"""Package the approved terminal with the user's contour; no RGB or engine edits."""
from pathlib import Path
import json, hashlib, struct, shutil, argparse
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'assets/generated/v13ent-terminal/user-contour-v4-20261114'
OLD = ROOT/'assets/hd/v13ent/terminal-natural-edge-v2'
ORIGINAL = ROOT/'assets/generated/v13ent-terminal/qwen21-indicator-v2-20261114/source.png'
OUT = ROOT/'assets/hd/v13ent/terminal-user-contour-v3'
RUNTIME = ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
BACKUP = ROOT/'build/backups/before-terminal-user-contour-v3-20261114'
ALLOWED = [str((RUNTIME/n).relative_to(ROOT).as_posix()) for n in
           ['asset-010.rgba','terminal-indicator-on.rgba','manifest.json']]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def package():
    OUT.mkdir(parents=True,exist_ok=True)
    original=np.array(Image.open(ORIGINAL).convert('RGBA'))
    matte=np.array(Image.open(SOURCE/'precise-opacity.png').convert('RGB'))[:,:,0]
    states=[]; arrays=[]
    for name in ['terminal-off','terminal-on']:
        im=Image.open(SOURCE/(name+'.png')).convert('RGBA'); a=np.array(im)
        old=np.array(Image.open(OLD/(name+'.png')).convert('RGBA'))
        assert a.shape==old.shape==original.shape==(212,128,4)
        assert np.array_equal(a[:,:,:3],old[:,:,:3]),'RGB must be byte-identical'
        assert np.array_equal(a[53:76,92:112],old[53:76,92:112]),'Lamp and socket changed'
        assert np.array_equal(a[:,:,3],matte)
        assert np.all(a[:,:,3]<=original[:,:,3]),'Original FRM support exceeded'
        assert np.any((a[:,:,3]>0)&(a[:,:,3]<255))
        shutil.copy2(SOURCE/(name+'.png'),OUT/(name+'.png'))
        raw=im.tobytes(); (OUT/(name+'.rgba')).write_bytes(b'F1HD'+struct.pack('<IIII',1,128,212,4)+raw)
        arrays.append(a)
        states.append(dict(state=name,png_sha256=sha(OUT/(name+'.png')),rgba_sha256=sha(OUT/(name+'.rgba')),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest()))
    assert np.array_equal(arrays[0][:,:,3],arrays[1][:,:,3])
    y,x=np.where(np.any(arrays[0]!=arrays[1],axis=2))
    assert len(x)==62 and [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]==[96,58,106,67]
    old_alpha=np.array(Image.open(OLD/'terminal-off.png').convert('RGBA'))[:,:,3]
    m=dict(native=[32,53],hd=[128,212],asset_id=10,fid=33554542,
           alpha_values=np.unique(matte).tolist(),
           alpha_policy='User red outline traced at 2x HD and area-antialiased in ComfyUI; capped to original FRM support. Actual scene background compositing required.',
           rgb_exact_previous=True,lamp_exact_previous=True,lamp_changed_pixels=62,
           removed_visible_pixels=int(np.sum((matte==0)&(old_alpha>0))),
           restored_inside_guide_pixels=int(np.sum((matte>0)&(old_alpha==0))),
           states=states,source=str(SOURCE),
           comfy_prompt_id=json.loads((SOURCE/'run.json').read_text())['prompt_id'],
           requires_soft_terminal_renderer=True,diffusion=False,
           guide_sha256=sha(SOURCE/'user-marked-reference.png'))
    save(OUT/'manifest.json',m)
    (OUT/'README.txt').write_text('Терминал V3: точная маска по красной разметке пользователя.\n'
        'RGB обоих состояний совпадает с V2. Лампа 500/1100 мс сохранена.\n'
        'Маска построена в ComfyUI, без новой диффузии; исходная поддержка FRM ограничивает силуэт.\n'
        'Размер 128x212, frame offsets и исходный игровой объект неизменны.\n'
        'Использовать с текущим EXE мягкого края, не устанавливать пакет V13 целиком.\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in m.items() if k not in ['states','source','alpha_policy']}))

def install():
    assert not BACKUP.exists(),'Existing backup: inspect before retry'
    assert sha(RUNTIME/'asset-010.rgba')==sha(OLD/'terminal-off.rgba')
    assert sha(RUNTIME/'terminal-indicator-on.rgba')==sha(OLD/'terminal-on.rgba')
    files=set((ROOT/'runtime/hd-world-pilot/data').rglob('*'))
    files.update((ROOT/'work/hd-world-pilot/fallout1-ce-main/src').rglob('*'))
    files.update(ROOT/p for p in ['runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/fallout.cfg','AGENTS.md','HD-TEXTURE-GUIDE.md'])
    baseline={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()}
    BACKUP.mkdir(parents=True)
    for name in ALLOWED+['build/hd-terminal-indicator/integration.json','work/hd-terminal-indicator/README.txt']:
        dest=BACKUP/name; dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    save(BACKUP/'baseline.json',baseline)
    m=json.loads((RUNTIME/'manifest.json').read_text());pack=json.loads((OUT/'manifest.json').read_text())
    for name in ALLOWED: assert sha(ROOT/name)==baseline[name]
    for src,dest in [('terminal-off.rgba','asset-010.rgba'),('terminal-on.rgba','terminal-indicator-on.rgba')]:
        shutil.copy2(OUT/src,RUNTIME/dest)
    row=next(r for r in m['assets'] if r['asset_id']==10)
    row.update(source_png=str(OUT/'terminal-off.png'),source_png_sha256=sha(OUT/'terminal-off.png'),
               runtime_file_sha256=sha(RUNTIME/'asset-010.rgba'),decoded_rgba_sha256=pack['states'][0]['decoded_rgba_sha256'],
               alpha_values=pack['alpha_values'],alpha_exact_original_nearest_neighbor=False,alpha_policy=pack['alpha_policy'])
    m['component_patches'].append(dict(component='terminal-user-contour',supersedes='terminal-natural-edge-v2',
        package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),animated_companion_file='terminal-indicator-on.rgba',
        animated_companion_sha256=sha(RUNTIME/'terminal-indicator-on.rgba'),requires_soft_terminal_renderer=True))
    save(RUNTIME/'manifest.json',m)
    print('Installed two terminal images and updated their runtime receipt; EXE unchanged.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['package','install']);a=p.parse_args()
    {'package':package,'install':install}[a.action]()
