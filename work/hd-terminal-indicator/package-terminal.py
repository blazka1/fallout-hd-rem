"""Verify and losslessly package the two Comfy-prepared terminal states."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,struct,shutil,argparse
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/generated/v13ent-terminal/qwen21-indicator-v2-20261114'
OUT=ROOT/'assets/hd/v13ent/terminal-indicator-v1'
RUNTIME=ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
BACKUP=ROOT/'build/backups/before-terminal-indicator-20261114'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def package():
 OUT.mkdir(parents=True,exist_ok=True)
 orig=np.array(Image.open(SOURCE/'source.png').convert('RGBA'))
 on=np.array(Image.open(SOURCE/'prepared/terminal-on.png').convert('RGBA'))
 off=np.array(Image.open(SOURCE/'prepared/terminal-off.png').convert('RGBA'))
 assert orig.shape==on.shape==off.shape==(212,128,4)
 assert np.array_equal(on[:,:,3],orig[:,:,3]) and np.array_equal(off[:,:,3],orig[:,:,3])
 y,x=np.where(np.any(on!=off,axis=2));assert 0<len(x)<150
 assert x.min()>=92 and x.max()<112 and y.min()>=52 and y.max()<76
 # Whole sprite transparency is inherited exactly; the new lamp changes no alpha.
 assert set(np.unique(on[:,:,3]).tolist())=={0,255}
 records=[]
 for name in ['terminal-off','terminal-on']:
  png=SOURCE/'prepared'/f'{name}.png';shutil.copy2(png,OUT/png.name)
  raw=Image.open(png).convert('RGBA').tobytes()
  target=OUT/f'{name}.rgba';target.write_bytes(b'F1HD'+struct.pack('<IIII',1,128,212,4)+raw)
  assert target.read_bytes()[20:]==raw
  records.append(dict(state=name,png_sha256=sha(OUT/png.name),runtime_sha256=sha(target),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest()))
 plan=dict(native=[32,53],hd=[128,212],original_fid=33554542,original_asset_id=10,alpha_exact=True,changed_lamp_pixels=len(x),lamp_hd_bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],period_ms=1600,on_ms=500,source=str(SOURCE),source_sha256=sha(SOURCE/'source.png'),qwen_prompt_id=json.loads((SOURCE/'run.json').read_text())['prompt_id'],preparation_prompt_id=json.loads((SOURCE/'prepared/run.json').read_text())['prompt_id'],states=records)
 save(OUT/'manifest.json',plan);print(json.dumps(plan))
def install_assets():
 baseline=json.loads((BACKUP/'baseline.json').read_text())
 for name in ['asset-010.rgba','manifest.json']:
  p=RUNTIME/name;key=p.relative_to(ROOT).as_posix();assert sha(p)==baseline[key],f'Runtime changed: {key}'
 package_manifest=json.loads((OUT/'manifest.json').read_text())
 for src,dst in [('terminal-off.rgba','asset-010.rgba'),('terminal-on.rgba','terminal-indicator-on.rgba')]:shutil.copy2(OUT/src,RUNTIME/dst)
 m=json.loads((RUNTIME/'manifest.json').read_text(encoding='utf-8-sig'))
 row=next(r for r in m['assets'] if r['asset_id']==10)
 row.update(source_png=str(OUT/'terminal-off.png'),source_png_sha256=sha(OUT/'terminal-off.png'),runtime_file_sha256=sha(RUNTIME/'asset-010.rgba'),decoded_rgba_sha256=package_manifest['states'][0]['decoded_rgba_sha256'])
 m.setdefault('component_patches',[]).append(dict(component='terminal-indicator',package=str(OUT),manifest_sha256=sha(OUT/'manifest.json'),animated_companion_file='terminal-indicator-on.rgba',animated_companion_sha256=sha(RUNTIME/'terminal-indicator-on.rgba'),scope='only asset 10 RGB plus optional lamp companion; registries, metadata, alpha and original data unchanged'))
 save(RUNTIME/'manifest.json',m)
 print('Installed only terminal base/companion and runtime asset receipt. EXE not changed.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['package','install-assets']);a=p.parse_args();{'package':package,'install-assets':install_assets}[a.action]()
