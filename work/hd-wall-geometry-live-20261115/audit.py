"""Validate world-space pixel agreement, registration and protected state."""
from pathlib import Path
import json,hashlib,itertools
import numpy as np
from PIL import Image
from bake import R,W,O,D,B,read,save,decode
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 j=read(O/'placements.json');rows=j['placements'];src=R/'runtime/hd-world-pilot/data/art/hd/world-pilot'
 ims={r['object']['id']:np.asarray(Image.open(O/'sprites'/f'wall-{r["object"]["id"]:04}.png').convert('RGBA')) for r in rows}
 pairs=0;samples=0;maxerr=0
 for a,b in itertools.combinations(rows,2):
  x,y,w,h=a['world_box'];xx,yy,ww,hh=b['world_box']
  l,t,r,bb=max(x,xx),max(y,yy),min(x+w,xx+ww),min(y+h,yy+hh)
  if l>=r or t>=bb:continue
  aa=ims[a['object']['id']][(t-y)*4:(bb-y)*4,(l-x)*4:(r-x)*4]
  ab=ims[b['object']['id']][(t-yy)*4:(bb-yy)*4,(l-xx)*4:(r-xx)*4]
  both=(aa[:,:,3]>0)&(ab[:,:,3]>0)
  if not both.any():continue
  e=int(np.abs(aa[:,:,:3].astype(np.int16)-ab[:,:,:3].astype(np.int16))[both].max())
  maxerr=max(maxerr,e);pairs+=1;samples+=int(both.sum());assert e==0,(a['object']['id'],b['object']['id'],e)
  # Repeated source types intentionally have position-specific appearances.
 for a in rows:
  rgba=ims[a['object']['id']];w,h=a['world_box'][2:];assert rgba.shape==(h*4,w*4,4)
  assert np.array_equal(rgba,decode(D/a['file']))
 before=decode(src/'vault-rock-a.rgba');after=decode(D/'vault-rock-a.rgba');assert np.array_equal(before[:,:,3],after[:,:,3])
 for id in [61,62,63]:
  for name in [f'asset-{id:03}']+([f'tile-{id:03}-v{v}' for v in range(1,4)] if id!=61 else []):
   assert np.array_equal(decode(src/f'{name}.rgba')[:,:,3],decode(D/f'{name}.rgba')[:,:,3])
 expected={r['file'] for r in rows}|{'wall-geometry.tsv','vault-rock-a.rgba','asset-061.rgba','asset-062.rgba','asset-063.rgba'}|{f'tile-{i:03}-v{v}.rgba' for i in [62,63] for v in [1,2,3]}
 untouched=[]
 for f in src.glob('*'):
  if f.is_file() and f.name not in expected:
   assert (D/f.name).exists() and sha(f)==sha(D/f.name),f.name
   untouched.append(f.name)
 save(B/'asset-audit.json',dict(registered_sprites=len(rows),resource_types=len({r['source'] for r in rows}),overlapping_pairs=pairs,shared_opaque_pixels=samples,maximum_overlap_rgb_difference=maxerr,door_alpha_exact=True,cutaway_alpha_exact=True,unchanged_other_runtime_assets=len(untouched),actual_contacts_note='Pairwise raster overlap equality; not a substitute for SDL camera/actor/scroll checks.'))
 print('AUDIT',len(rows),'sprites,',pairs,'overlap pairs,',samples,'identical shared pixels;',len(untouched),'other files unchanged')
if __name__=='__main__':main()
