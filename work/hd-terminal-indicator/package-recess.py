"""Lossless isolated frame patch; preserve the approved terminal/lamp assets."""
from pathlib import Path
import json,hashlib,struct,shutil
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/generated/v13ent-terminal/recess-v4-20261114'
OUT=ROOT/'assets/hd/v13ent/terminal-recess-v4'
RUNTIME=ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
BACKUP=ROOT/'build/backups/before-terminal-halo-v4-20261114'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
baseline=json.loads((BACKUP/'runtime-baseline.json').read_text())
for name in ['asset-016.rgba','manifest.json']:
    p=RUNTIME/name;assert sha(p)==baseline[p.relative_to(ROOT).as_posix()]
old=Image.open(ROOT/'assets/hd/v13ent/v14-campfire-x4/art/scenery/v13secr3.frm.png').convert('RGBA')
im=Image.open(SOURCE/'prepared/vault-frame.png').convert('RGBA');a=np.array(im);b=np.array(old)
assert a.shape==b.shape==(896,1368,4)
expected=b[:,:,3].copy();expected[628:840,292:424]=255
assert np.array_equal(a[:,:,3],expected)
assert set(np.unique(a[:,:,3]))=={0,255}
assert np.array_equal(a[:,:,3],np.repeat(np.repeat(a[::4,::4,3],4,0),4,1))
changed=np.any(a[:,:,:3]!=b[:,:,:3],axis=2);outside=changed.copy();outside[608:852,276:436]=False
assert not np.any(outside),'Changes outside local panel'
assert np.count_nonzero(changed)>1000
OUT.mkdir(exist_ok=True);shutil.copy2(SOURCE/'prepared/vault-frame.png',OUT/'vault-frame.png')
raw=im.tobytes();(OUT/'vault-frame.rgba').write_bytes(b'F1HD'+struct.pack('<IIII',1,1368,896,4)+raw)
pack=dict(resource='art/scenery/v13secr3.frm',asset_id=16,native=[342,224],hd=[1368,896],
    rgb_patch=[276,608,160,244],alpha_addition=[292,628,132,212],alpha_policy='Original 4x native binary alpha plus the old terminal recess only; requires the bounded HD-only frame fill hook.',
    rgb_changed_pixels=int(np.count_nonzero(changed)),added_native_cells=int(np.sum((a[::4,::4,3]>0)&(b[::4,::4,3]==0))),
    source=str(SOURCE),png_sha256=sha(OUT/'vault-frame.png'),rgba_sha256=sha(OUT/'vault-frame.rgba'),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest(),
    qwen_prompt_id=json.loads((SOURCE/'run.json').read_text())['prompt_id'],comfy_preparation_prompt_id=json.loads((SOURCE/'prepared/run.json').read_text())['prompt_id'],
    approved_terminal_package='assets/hd/v13ent/terminal-user-contour-v3',terminal_files_unchanged=True)
save(OUT/'manifest.json',pack)
m=json.loads((RUNTIME/'manifest.json').read_text());row=next(r for r in m['assets'] if r['asset_id']==16)
shutil.copy2(OUT/'vault-frame.rgba',RUNTIME/'asset-016.rgba')
row.update(source_png=str(OUT/'vault-frame.png'),source_png_sha256=pack['png_sha256'],runtime_file_sha256=pack['rgba_sha256'],
    decoded_rgba_sha256=pack['decoded_rgba_sha256'],alpha_exact_original_nearest_neighbor=False,alpha_policy=pack['alpha_policy'])
m['component_patches'].append(dict(component='terminal-recess-v4',package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),
    asset_id=16,requires_hd_recess_renderer=True,preserves_terminal_package=pack['approved_terminal_package']))
save(RUNTIME/'manifest.json',m)
print(json.dumps(dict(packaged=True,changed_rgb=pack['rgb_changed_pixels'],added_native_cells=pack['added_native_cells'])))
