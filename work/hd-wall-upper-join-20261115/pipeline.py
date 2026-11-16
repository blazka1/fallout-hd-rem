"""Connected upper wall material repair through the existing local Comfy workflow."""
from pathlib import Path
import sys,uuid,struct,shutil,hashlib,json,re,subprocess,importlib.util
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('wall_helpers',R/'work/hd-cave-wall-variety-20261115/pipeline.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);p=w.p
OUT=R/'assets/generated/v13ent-wall-upper-join/v1-20261115';p.OUT=OUT
B=R/'build/hd-wall-upper-join-20261115';BACK=R/'build/backups/before-wall-upper-join-20261115'
RT=R/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot';PACK=R/'assets/hd/v13ent/wall-upper-join-v1'
POS={120:(640,102),121:(672,102),122:(704,102),123:(736,102),130:(768,103)}
def idle():
 q=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name '*fallout*' -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
 assert q.stdout.strip()=='0','Fallout is running'
def prepare():
 if (OUT/'inventory.json').exists():return
 registry=p.read(DATA/'manifest.json');byid={a['asset_id']:a for a in registry['assets']}
 rows=[]
 for a in registry['assets']:
  base=a.get('base_asset_id',a['asset_id'])
  if base not in POS:continue
  row=dict(a,base=base);rows.append(row)
  w.decode(DATA/a['filename']).save(OUT/'inputs'/('asset-%03d.png'%a['asset_id']))
  shutil.copy2(DATA/a['filename'],BACK/a['filename'])
 assert len(rows)==13,len(rows)
 p.save(OUT/'inventory.json',rows)
 p.save(BACK/'runtime-before.json',{str(f.relative_to(R)):p.sha(f) for f in RT.rglob('*') if f.is_file()})
 p.save(BACK/'protected.json',{str(f.relative_to(R)):p.sha(f) for f in [R/'AGENTS.md',R/'HD-TEXTURE-GUIDE.md']})
 owners=np.fromfile(B/'before/owners.bin',np.uint32).reshape(540,960)
 canvas=np.zeros((864,960,3),np.uint8);cache={}
 shot=np.array(Image.open(B/'before/entrance-hd.png').convert('RGB').resize((3840,2160),Image.Resampling.NEAREST))
 for y in range(216):
  for x in range(240):
   token=int(owners[40+y,600+x]);id=token>>24;t=token&0xffffff
   if id in byid and (id<224):
    if id not in cache:cache[id]=np.array(w.decode(DATA/byid[id]['filename']))
    a=cache[id];nw=a.shape[1]//4;u=t%nw*4;v=t//nw*4
    if v+4<=a.shape[0]:canvas[y*4:y*4+4,x*4:x*4+4]=a[v:v+4,u:u+4,:3];continue
   canvas[y*4:y*4+4,x*4:x*4+4]=shot[(40+y)*4:(41+y)*4,(600+x)*4:(601+x)*4]
 Image.fromarray(canvas).save(OUT/'inputs/context.png')
 w.decode(DATA/byid[115]['filename']).save(OUT/'inputs/neighbor-material.png')
 p.save(OUT/'registration.json',dict(context_native=[600,40,240,216],density=4,positions=POS))
 print('Exported current connected wall and 13 registered family images',flush=True)
def graph():
 g={};outputs={};prefix='fallout1_upper_wall_join/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return[k,0]
 def load(f):return add('LoadImage',image=p.upload(f))
 def save(n,name):node=add('SaveImage',images=n,filename_prefix=prefix+'/'+name);outputs[node[0]]=name+'.png'
 return g,outputs,add,load,save
def donor():
 d=OUT/'donor-v1'
 if (d/'run.json').exists():p.execute(d,{},{});return
 g,outputs,add,load,save=graph();src=load(OUT/'inputs/context.png');ref=load(OUT/'inputs/neighbor-material.png')
 prompt='''Repair the material discontinuity in this EXISTING Fallout cave wall. The central wall panel below y248 looks like a separate brighter slab pasted onto the cave: large flat diagonal plates and a straight upper texture lip. Replace that incompatible surface in the CENTRAL upper wall x160 to x800, y248 to y560 with the SAME darker rough fractured neutral charcoal stone as the neighboring left and right wall. Image 2 is that neighboring wall material reference. Preserve exact scene, camera, sprite positions, all silhouettes and lighting direction. Make the central area visually one continuous wall: finer irregular hard stone fractures, coarse rock grain, dark vertical-to-diagonal grooves continuing from adjacent walls, with restrained subdued highlights. The upper edge at y248 must disappear as a mechanical straight boundary. The dark densely striated rock above should transition NATURALLY and GRADUALLY through irregular shadowed creases into the wall face below. No ledge, cap, bright horizontal lip, large smooth flat slab or rectangular patch. Avoid the conspicuous broad pale diagonal plates currently in the central panel. Keep the upper dark background above y190 exactly as it is, keep the far left and right neighboring walls exactly as they are, and keep all lower rocks, columns, mushrooms and floor unchanged below y600. Do not add objects, holes, moss, mushrooms, dramatic new cracks, broad highlights or different hues. This is a focused surface-material and tonal repair, NOT a new scene or redesigned geometry. Stone stays hard, granular and sharply fractured; no melted soft rock or blur. Output same composition and dimensions, opaque image.'''
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
 clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
 vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors');model=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':src,'images.image_2':ref})
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15153101,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 save(add('VAEDecode',samples=sample,vae=vae),'raw');d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.execute(d,g,outputs)
def fit():
 d=OUT/'fit-v2'
 if (d/'run.json').exists():p.execute(d,{},{});return
 # Exact semantic export of CE ownership, not painted image content.
 owners=np.fromfile(B/'before/owners.bin',np.uint32).reshape(540,960)[40:256,600:840]>>24
 data=np.isin(owners,[186,189,122,123,197]).astype(np.uint8)*255
 Image.fromarray(np.repeat(np.repeat(data,4,axis=0),4,axis=1)).save(OUT/'inputs/wall-ownership-mask.png')
 g,outputs,add,load,save=graph();raw=load(OUT/'donor-v1/raw.png')
 raw=add('ImageScale',image=raw,upscale_method='lanczos',width=960,height=864,crop='disabled')
 full=add('SolidMask',value=0.,width=960,height=864)
 band=add('SolidMask',value=1.,width=664,height=320)
 band=add('FeatherMask',mask=band,left=24,top=0,right=32,bottom=128)
 full=add('MaskComposite',destination=full,source=band,x=160,y=248,operation='add')
 owned=add('ImageToMask',image=load(OUT/'inputs/wall-ownership-mask.png'),channel='red')
 interior=add('GrowMask',mask=owned,expand=-4,tapered_corners=True)
 interior=add('ImageBlur',image=add('MaskToImage',mask=interior),blur_radius=4,sigma=2.)
 interior=add('ImageToMask',image=interior,channel='red')
 owned=add('MaskComposite',destination=owned,source=interior,x=0,y=0,operation='multiply')
 full=add('MaskComposite',destination=full,source=owned,x=0,y=0,operation='multiply')
 full=add('MaskToImage',mask=full)
 for a in p.read(OUT/'inventory.json'):
  x,y=POS[a['base']];x=(x-600)*4;y=(y-40)*4;width=a['width'];height=a['height']
  donor=add('ImageCrop',image=raw,x=x,y=y,width=width,height=height)
  mask=add('ImageCrop',image=full,x=x,y=y,width=width,height=height)
  mask=add('ImageToMask',image=mask,channel='red')
  old=load(OUT/'inputs'/('asset-%03d.png'%a['asset_id']))
  result=add('ImageCompositeMasked',destination=old,source=donor,x=0,y=0,resize_source=False,mask=mask)
  result=add('JoinImageWithAlpha',image=result,alpha=[old[0],1]);save(result,'asset-%03d'%a['asset_id'])
 p.execute(d,g,outputs)
def stage():
 idle();records=[]
 for a in p.read(OUT/'inventory.json'):
  id=a['asset_id'];f=a['filename'];src=OUT/'fit-v2'/('asset-%03d.png'%id)
  old=np.array(Image.open(OUT/'inputs'/('asset-%03d.png'%id)).convert('RGBA'));new=np.array(Image.open(src).convert('RGBA'))
  assert old.shape==new.shape and np.array_equal(old[:,:,3],new[:,:,3])
  limit=320-(POS[a['base']][1]-102)*4
  assert np.array_equal(old[limit:],new[limit:]),id
  assert p.sha(DATA/f)==p.sha(BACK/f),'concurrent edit: '+f
  im=Image.open(src).convert('RGBA');out=PACK/f
  out.write_bytes(struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes())
  shutil.copy2(src,PACK/src.name);shutil.copy2(out,DATA/f)
  records.append(dict(id=id,base=a['base'],file=f,png=src.name,runtime_sha256=p.sha(out),png_sha256=p.sha(src),decoded_rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest(),alpha_exact=True,protected_lower_from=limit,changed_pixels=int(np.any(old!=new,2).sum())))
 p.save(PACK/'manifest.json',dict(status='staged-for-render-check',records=records));print('Staged 13 upper wall family strips; alpha and lower surfaces exact',flush=True)
if __name__=='__main__':{'prepare':prepare,'donor':donor,'fit':fit,'stage':stage}[sys.argv[1]]()
