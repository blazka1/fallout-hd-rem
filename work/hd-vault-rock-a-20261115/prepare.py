"""Variant A: native Comfy fitting, lossless packaging, narrowly scoped runtime install."""
import sys,json,hashlib,struct,shutil,subprocess,uuid
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'work/hd-vault-rock-prototypes-20261115'))
import generate as z
p=z.p
OUT=R/'assets/generated/v13ent-vault-rock-a/v1-20261115';p.OUT=OUT
PACK=R/'assets/hd/v13ent/vault-rock-a-v1'
BACK=R/'build/backups/before-vault-rock-a-20261115'
RT=R/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot'
def idle():
 r=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name '*fallout*' -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
 assert r.stdout.strip()=='0','Fallout running'
def baseline():
 OUT.mkdir(parents=True,exist_ok=True)
 if not (BACK/'runtime-before.json').exists():
  p.save(BACK/'runtime-before.json',{str(f.relative_to(R)):p.sha(f) for f in RT.rglob('*') if f.is_file()})
  p.save(BACK/'protected.json',{str(f.relative_to(R)):p.sha(f) for f in [R/'AGENTS.md',R/'HD-TEXTURE-GUIDE.md']})
def prepare():
 baseline();d=OUT/'fit';g={};outputs={}
 if (d/'run.json').exists():p.execute(d,{},{});return
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return[k,0]
 source=R/'assets/generated/v13ent-vault-rock-prototypes/v1-20261115/preview-v2/a-selected.png'
 n=add('LoadImage',image=p.upload(source));n=add('JoinImageWithAlpha',image=n,alpha=[n[0],1])
 n=add('ImageCrop',image=n,x=68,y=32,width=248,height=960)
 n=add('ImageScale',image=n,upscale_method='lanczos',width=124,height=480,crop='disabled')
 prefix='fallout1_vault_rock_a/'+uuid.uuid4().hex
 saved=add('SaveImage',images=n,filename_prefix=prefix+'/sprite');outputs[saved[0]]='sprite.png'
 blank=add('EmptyImage',width=512,height=512,batch_size=1,color=0)
 blank=add('JoinImageWithAlpha',image=blank,alpha=add('SolidMask',value=1.,width=512,height=512))
 # Copy RGBA into transparent atlas; alpha is preserved, not blended twice.
 atlas=add('ImageCompositeMasked',destination=blank,source=n,x=0,y=0,resize_source=False)
 saved=add('SaveImage',images=atlas,filename_prefix=prefix+'/atlas');outputs[saved[0]]='atlas.png'
 p.execute(d,g,outputs)
def stage():
 idle();baseline();im=Image.open(OUT/'fit/atlas.png').convert('RGBA');assert im.size==(512,512)
 PACK.mkdir(parents=True,exist_ok=True)
 target=PACK/'vault-rock-a.rgba';target.write_bytes(struct.pack('<4sIIII',b'F1HD',1,512,512,4)+im.tobytes())
 for f in ['sprite.png','atlas.png']:shutil.copy2(OUT/'fit'/f,PACK/f)
 assets=(BACK/'cave-variety-assets.tsv').read_text();placements=(BACK/'cave-variety-placements.tsv').read_text()
 assert len([s for s in placements.splitlines() if s and not s.startswith('#')])==76
 assert not any(s.startswith('252 ') for s in assets.splitlines())
 for f in ['cave-variety-assets.tsv','cave-variety-placements.tsv']:
  assert p.sha(DATA/f)==p.sha(BACK/f),'concurrent runtime edit: '+f
 assets=assets.rstrip()+'\n252 128 128 vault-rock-a.rgba\n'
 placements=placements.rstrip()+'\n76 252 50331705 50331855 17285 0 0 0 0 252 31 120 0 0 124 480 0 0 31 120\n'
 shutil.copy2(target,DATA/target.name)
 for f,s in [('cave-variety-assets.tsv',assets),('cave-variety-placements.tsv',placements)]:
  (PACK/f).write_text(s,encoding='utf-8');(DATA/f).write_text(s,encoding='utf-8')
 p.save(PACK/'manifest.json',dict(status='staged-for-engine-check',asset_id=252,object_id=252,fid=50331705,pid=50331855,tile=17285,
  original_native_size=[31,120],draw_native_size=[31,120],crop_hd=[0,0,124,480],atlas=[512,512],
  source='assets/generated/v13ent-vault-rock-prototypes/v1-20261115/preview-v2/a-selected.png',runtime_sha256=p.sha(target),
  rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest(),new_alpha=True,map_modified=False))
 print('Staged variant A, exact object 252; existing texture images untouched',flush=True)
def refine():
 idle();d=OUT/'fit-seam-v4';g={};outputs={}
 if not (d/'run.json').exists():
  def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return[k,0]
  new=add('LoadImage',image=p.upload(OUT/'fit/sprite.png'))
  old=add('LoadImage',image=p.upload(R/'assets/generated/v13ent-vault-rock-prototypes/v1-20261115/inputs/original.png'))
  mask=add('SolidMask',value=0.,width=124,height=480)
  for x in range(100,124):
   strip=add('SolidMask',value=(x-99)/24.,width=1,height=480)
   mask=add('MaskComposite',destination=mask,source=strip,x=x,y=0,operation='add')
  mask=add('MaskComposite',destination=mask,source=add('InvertMask',mask=[old[0],1]),x=0,y=0,operation='multiply')
  blended=add('ImageCompositeMasked',destination=new,source=old,mask=mask,x=0,y=0,resize_source=False)
  # Counter float inversion roundoff before SaveImage's uint8 truncation.
  exactAlpha=add('MaskComposite',destination=[new[0],1],source=add('SolidMask',value=.000001,width=124,height=480),x=0,y=0,operation='subtract')
  # This is an attachment cut, not an exposed silhouette: remove the
  # generation's transparent rim only in the last four HD columns where
  # the adjacent A interior is opaque. Keep top/bottom tips and left contour.
  inside=add('MaskToImage',mask=add('InvertMask',mask=[new[0],1]))
  inside=add('ImageCrop',image=inside,x=119,y=0,width=1,height=480)
  inside=add('ImageScale',image=inside,upscale_method='nearest-exact',width=4,height=480,crop='disabled')
  inside=add('ThresholdMask',mask=add('ImageToMask',image=inside,channel='red'),value=.9)
  edge=add('SolidMask',value=0.,width=124,height=480)
  edge=add('MaskComposite',destination=edge,source=inside,x=120,y=0,operation='add')
  edge=add('MaskComposite',destination=edge,source=add('InvertMask',mask=[old[0],1]),x=0,y=0,operation='multiply')
  exactAlpha=add('MaskComposite',destination=exactAlpha,source=edge,x=0,y=0,operation='subtract')
  sprite=add('JoinImageWithAlpha',image=blended,alpha=exactAlpha)
  prefix='fallout1_vault_rock_a/seam-'+uuid.uuid4().hex
  n=add('SaveImage',images=sprite,filename_prefix=prefix+'/sprite');outputs[n[0]]='sprite.png'
  blank=add('EmptyImage',width=512,height=512,batch_size=1,color=0)
  blank=add('JoinImageWithAlpha',image=blank,alpha=add('SolidMask',value=1.,width=512,height=512))
  atlas=add('ImageCompositeMasked',destination=blank,source=sprite,x=0,y=0,resize_source=False)
  n=add('SaveImage',images=atlas,filename_prefix=prefix+'/atlas');outputs[n[0]]='atlas.png'
  p.execute(d,g,outputs)
 else:p.execute(d,{}, {})
 import numpy as np
 a=np.array(Image.open(OUT/'fit/sprite.png'));b=np.array(Image.open(d/'sprite.png'))
 assert np.array_equal(a[:,:120,3],b[:,:120,3]) and np.array_equal(a[:,:100],b[:,:100])
 m=p.read(PACK/'manifest.json');assert p.sha(DATA/'vault-rock-a.rgba')==m['runtime_sha256']
 im=Image.open(d/'atlas.png').convert('RGBA');target=PACK/'vault-rock-a.rgba'
 target.write_bytes(struct.pack('<4sIIII',b'F1HD',1,512,512,4)+im.tobytes())
 for f in ['sprite.png','atlas.png']:shutil.copy2(d/f,PACK/f)
 shutil.copy2(target,DATA/target.name)
 m.update(runtime_sha256=p.sha(target),rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest(),seam_fit='rightmost 24 HD pixels blend to former wall material; attachment alpha closes last 4 HD columns only where adjacent interior is opaque; left contour and all other alpha exact')
 p.save(PACK/'manifest.json',m)
 print('Seam fitted; approved A exposed contour exact, attachment rim closed',flush=True)
if __name__=='__main__':
 {'prepare':prepare,'stage':stage,'refine':refine}[sys.argv[1]]()
