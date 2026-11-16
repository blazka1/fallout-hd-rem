"""Lossless local edge patch, with the approved lamp preserved byte for byte."""
from pathlib import Path
import json,hashlib,struct,shutil,argparse
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/generated/v13ent-terminal/natural-edge-v3-20261114'
OLD=ROOT/'assets/hd/v13ent/terminal-indicator-v1'
OUT=ROOT/'assets/hd/v13ent/terminal-natural-edge-v2'
RUNTIME=ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
BACKUP=ROOT/'build/backups/before-terminal-natural-edge-v2-20261114'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def package():
 OUT.mkdir(parents=True,exist_ok=True);states=[];arrays=[]
 original=np.array(Image.open(OLD/'terminal-off.png').convert('RGBA'))
 for name in ['terminal-off','terminal-on']:
  im=Image.open(SOURCE/(name+'.png')).convert('RGBA');a=np.array(im);old=np.array(Image.open(OLD/(name+'.png')).convert('RGBA'))
  assert a.shape==old.shape==(212,128,4)
  assert np.array_equal(a[53:76,92:112],old[53:76,92:112]),'Lamp and socket must be exact'
  assert np.all(a[:,:,3]<=old[:,:,3]) and np.any((a[:,:,3]>0)&(a[:,:,3]<255))
  shutil.copy2(SOURCE/(name+'.png'),OUT/(name+'.png'))
  raw=im.tobytes();(OUT/(name+'.rgba')).write_bytes(b'F1HD'+struct.pack('<IIII',1,128,212,4)+raw)
  arrays.append(a);states.append(dict(state=name,png_sha256=sha(OUT/(name+'.png')),rgba_sha256=sha(OUT/(name+'.rgba')),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest()))
 y,x=np.where(np.any(arrays[0]!=arrays[1],axis=2));assert len(x)==62
 assert np.array_equal(arrays[0][:,:,3],arrays[1][:,:,3])
 m=dict(native=[32,53],hd=[128,212],alpha_values=np.unique(arrays[0][:,:,3]).tolist(),alpha_policy='Original support contracted by 2 HD pixels, next pixel antialiased; top cable protected. No silhouette expansion. Real background compositing required.',lamp_exact_previous=True,lamp_changed_pixels=62,body_and_screen_unchanged_outside_five_pixel_edge=True,states=states,source=str(SOURCE),comfy_prompt_id=json.loads((SOURCE/'run.json').read_text())['prompt_id'],requires_soft_terminal_renderer=True)
 save(OUT/'manifest.json',m);print(json.dumps(m))
def install():
 baseline=json.loads((BACKUP/'baseline.json').read_text())
 for name in ['asset-010.rgba','terminal-indicator-on.rgba','manifest.json']:
  p=RUNTIME/name;assert sha(p)==baseline[p.relative_to(ROOT).as_posix()],str(p)
 m=json.loads((RUNTIME/'manifest.json').read_text());pack=json.loads((OUT/'manifest.json').read_text())
 for src,dest in [('terminal-off.rgba','asset-010.rgba'),('terminal-on.rgba','terminal-indicator-on.rgba')]:shutil.copy2(OUT/src,RUNTIME/dest)
 row=next(r for r in m['assets'] if r['asset_id']==10)
 row.update(source_png=str(OUT/'terminal-off.png'),source_png_sha256=sha(OUT/'terminal-off.png'),runtime_file_sha256=sha(RUNTIME/'asset-010.rgba'),decoded_rgba_sha256=pack['states'][0]['decoded_rgba_sha256'],alpha_values=pack['alpha_values'],alpha_exact_original_nearest_neighbor=False,alpha_policy=pack['alpha_policy'])
 m['component_patches'].append(dict(component='terminal-natural-edge',supersedes='terminal-indicator-v1',package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),animated_companion_file='terminal-indicator-on.rgba',animated_companion_sha256=sha(RUNTIME/'terminal-indicator-on.rgba'),requires_soft_terminal_renderer=True))
 save(RUNTIME/'manifest.json',m);print('Only two terminal images and runtime receipt replaced')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['package','install']);a=p.parse_args();{'package':package,'install':install}[a.action]()
