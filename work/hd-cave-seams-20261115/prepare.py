"""Targeted Comfy edge repairs, retaining native registration and alpha."""
from pathlib import Path
import sys,uuid
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hd-cave-wall-variety-20261115'))
import pipeline as w
p=w.p;R=w.R;OUT=R/'assets/generated/v13ent-cave-seams/v1-20261115';p.OUT=OUT

def graph():
 g={};outputs={};prefix='fallout1_cave_seams/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 def save(im,name):n=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[n[0]]=name+'.png'
 return g,outputs,add,load,save

def walls():
 d=OUT/'walls-v1'
 if (d/'run.json').exists():p.execute(d,{},{});return
 g,outputs,add,load,save=graph();plan=p.read(R/'assets/generated/v13ent-wall-variety/style-v1-20261115/plan.json');byid={x['asset_id']:x for x in plan['walls'].values()};records=[]
 for a in p.read(OUT/'inventory.json'):
  id=a['asset_id'];base=a.get('base_asset_id',id)
  if base not in [120,121,122,123,130]:continue
  oldpath=R/'assets/generated/v13ent-wall-variety/style-v1-20261115/inputs/walls'/(Path(byid[base]['original_resource']).stem+'.png')
  current=load(OUT/'inputs'/('asset-%03d.png'%id));old=load(oldpath);width,height=a['width'],a['height']
  # Retain the old connected roof and ease into the new material well below it.
  mask=add('SolidMask',value=0.,width=width,height=height)
  band=add('SolidMask',value=1.,width=width,height=round(height*.40));band=add('FeatherMask',mask=band,left=0,top=0,right=0,bottom=round(height*.23))
  mask=add('MaskComposite',destination=mask,source=band,x=0,y=0,operation='add')
  opaque=add('InvertMask',mask=[current[0],1]);mask=add('MaskComposite',destination=mask,source=opaque,x=0,y=0,operation='multiply')
  result=add('ImageCompositeMasked',destination=current,source=old,x=0,y=0,resize_source=False,mask=mask);result=add('JoinImageWithAlpha',image=result,alpha=[current[0],1]);save(result,'asset-%03d'%id)
  records.append(dict(id=id,base=base,file=a['filename'],original=str(oldpath.relative_to(R)),protected_lower_from=round(height*.40),alpha='exact current'))
 p.save(d/'records.json',records);p.execute(d,g,outputs)

def door_donor():
 d=OUT/'door-donor'
 if (d/'run.json').exists():p.execute(d,{},{});return
 g,outputs,add,load,save=graph();src=load(OUT/'inputs/asset-160.png');src=add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
 crop=add('ImageCrop',image=src,x=588,y=0,width=168,height=152);crop=add('ImageScale',image=crop,upscale_method='lanczos',width=672,height=608,crop='disabled');save(crop,'input')
 frame=load(OUT/'inputs/asset-016.png');frame=add('ImageCrop',image=frame,x=940,y=60,width=240,height=280)
 prompt='The first image is a close crop of the upper-right fixed metal wall inside a Fallout vault doorway, with transparent space above its sloping top edge. Repair ONLY the small ragged black wedges, black spikes and damaged pixel-like fringe along the upper diagonal cap and its left upper corner. Restore a clean continuous angled metal bevel with restrained crisp edges, no jagged black teeth or black holes on the metal. Keep the EXACT wall angle, position, shape, narrow panel lines, perspective, dark weathered brown iron color, fine rusty surface and subdued lighting. The second image shows the neighboring vault FRAME for material and joining context only. Do not copy it over the first. No new beams, panels, bolts, symbols, changed camera or resized object. Preserve the transparent background, preserve the lower panel and its seams. Fill only accidental black surface gaps with consistent existing metal and a straight continuous thin cap.'
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default');clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default');vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors');model=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':crop,'images.image_2':frame})
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15119911,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 decoded=add('VAEDecode',samples=sample,vae=vae);save(decoded,'raw');d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.execute(d,g,outputs)

def wall_donor():
 d=OUT/'wall-donor'
 if (d/'run.json').exists():p.execute(d,{},{});return
 # Exact unlit export of the real renderer's ownership, not a new arrangement.
 diag=R/'build/hd-cave-seams-20261115/diagnostic';owners=np.fromfile(diag/'owners.bin',np.uint32).reshape(540,960)
 registry={a['asset_id']:a for a in p.read(w.DATA/'manifest.json')['assets']};cache={};canvas=np.zeros((840,960,3),np.uint8)
 screenshot=np.array(Image.open(diag/'entrance-hd.png').convert('RGB').resize((3840,2160),Image.Resampling.NEAREST))
 for yy in range(210):
  for xx in range(240):
   token=int(owners[40+yy,600+xx]);id=token>>24;t=token&0xffffff
   if id in registry and not 224<=id<=251:
    if id not in cache:cache[id]=np.array(w.decode(w.DATA/registry[id]['filename']))
    a=cache[id];nw=a.shape[1]//4;u=t%nw*4;v=t//nw*4
    if v+4<=a.shape[0]:canvas[yy*4:yy*4+4,xx*4:xx*4+4]=a[v:v+4,u:u+4,:3];continue
   canvas[yy*4:yy*4+4,xx*4:xx*4+4]=screenshot[(40+yy)*4:(41+yy)*4,(600+xx)*4:(601+xx)*4]
 d.mkdir(parents=True,exist_ok=True);Image.fromarray(canvas).save(d/'input.png')
 g,outputs,add,load,save=graph();src=load(d/'input.png')
 prompt='Repair ONLY the artificial thin HORIZONTAL TEXTURE SEAM near the upper third of this connected Fallout cave wall. Several narrow wall sprite slices start on a mechanically straight horizontal line around image y=248. Remove this rectangular band and mismatched bright lip. Continue the SAME dark grey fractured rock relief smoothly from the surrounding sloping upper rock surface into the vertical wall below, with irregular natural transitions. No horizontal shelf, ledge, cut stone blocks, rectangular tile edges or pale strip. The broad upper dark rock mass stays dark, rugged and at the exact same height and silhouette. Preserve its existing diagonal grain and color. Keep the exact original camera, connected wall geometry, every rock contour, lower wall, mushrooms, moss, ground rocks, columns and all other objects. Edit only a narrow transition band around that seam, between y=190 and y=430, keeping everything above and below unchanged. Dark neutral grey Fallout stone, crisp irregular fractures, no change of hue or light direction, no smoother clay, no new objects, no extra large cracks, no color shift. This is a seamless local material repair of one continuous wall, NOT separately redrawn pillars or isolated slabs.'
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default');clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default');vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors');model=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':src})
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15119912,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 decoded=add('VAEDecode',samples=sample,vae=vae);save(decoded,'raw');(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.execute(d,g,outputs)

def door_prepare():
 d=OUT/'door-prepared-v4'
 if (d/'run.json').exists():p.execute(d,{},{});return
 g,outputs,add,load,save=graph();raw=load(OUT/'door-donor/raw.png');raw=add('ImageScale',image=raw,upscale_method='lanczos',width=168,height=152,crop='disabled')
 # The generated cap starts lower than the source fringe. Sample its intact
 # interior into that narrow fringe instead of leaving the old black wedges.
 donor=add('ImageCrop',image=raw,x=8,y=20,width=160,height=132)
 raw=add('ImageCompositeMasked',destination=raw,source=donor,x=0,y=0,resize_source=False)
 # Only the fixed top cap, shared by every animation frame.
 mask=add('SolidMask',value=0.,width=168,height=152)
 for x in range(44,168):
  edge=max(0,round((x-50)*.60));y0=max(0,edge-7);y1=min(151,edge+17)
  band=add('SolidMask',value=1.,width=1,height=y1-y0+1);mask=add('MaskComposite',destination=mask,source=band,x=x,y=y0,operation='add')
 maskim=add('ImageBlur',image=add('MaskToImage',mask=mask),blur_radius=2,sigma=1.);mask=add('ImageToMask',image=maskim,channel='red')
 # The marked defect is the left tip of this cap. Keep the rest of the
 # already aligned long metal edge byte-identical to the installed original.
 local=add('SolidMask',value=0.,width=168,height=152)
 tip=add('SolidMask',value=1.,width=44,height=40);tip=add('FeatherMask',mask=tip,left=4,top=0,right=8,bottom=8)
 local=add('MaskComposite',destination=local,source=tip,x=42,y=0,operation='add')
 mask=add('MaskComposite',destination=mask,source=local,x=0,y=0,operation='multiply')
 red=add('ImageToMask',image=raw,channel='red');blue=add('ImageToMask',image=raw,channel='blue');bg=add('MaskComposite',destination=blue,source=red,x=0,y=0,operation='subtract');bg=add('ThresholdMask',mask=bg,value=.04);mask=add('MaskComposite',destination=mask,source=add('InvertMask',mask=bg),x=0,y=0,operation='multiply')
 records=[]
 for id in range(160,175):
  old=load(OUT/'inputs'/('asset-%03d.png'%id));result=add('ImageCompositeMasked',destination=old,source=raw,x=588,y=0,resize_source=False,mask=mask);result=add('JoinImageWithAlpha',image=result,alpha=[old[0],1]);save(result,'asset-%03d'%id);records.append(dict(id=id,file='asset-%03d.rgba'%id,edit_box=[588,0,168,152],alpha='exact current'))
 p.save(d/'records.json',records);p.execute(d,g,outputs)

def wall_prepare():
 d=OUT/'walls-v2'
 if (d/'run.json').exists():p.execute(d,{},{});return
 g,outputs,add,load,save=graph();raw=load(OUT/'wall-donor/raw.png');raw=add('ImageScale',image=raw,upscale_method='lanczos',width=960,height=840,crop='disabled')
 positions={120:640,121:672,122:704,123:736,130:768};records=[]
 for a in p.read(OUT/'inventory.json'):
  id=a['asset_id'];base=a.get('base_asset_id',id)
  if base not in positions:continue
  current=load(OUT/'inputs'/('asset-%03d.png'%id));width,height=a['width'],a['height']
  donor=add('ImageCrop',image=raw,x=(positions[base]-600)*4,y=(102-40)*4,width=width,height=height)
  mask=add('SolidMask',value=0.,width=width,height=height);band=add('SolidMask',value=1.,width=width,height=184);band=add('FeatherMask',mask=band,left=0,top=0,right=0,bottom=88);mask=add('MaskComposite',destination=mask,source=band,x=0,y=0,operation='add')
  result=add('ImageCompositeMasked',destination=current,source=donor,x=0,y=0,resize_source=False,mask=mask);result=add('JoinImageWithAlpha',image=result,alpha=[current[0],1]);save(result,'asset-%03d'%id)
  records.append(dict(id=id,base=base,file=a['filename'],protected_lower_from=184,alpha='exact current',scene_crop=[(positions[base]-600)*4,248,width,height]))
 p.save(d/'records.json',records);p.execute(d,g,outputs)

if __name__=='__main__':{'walls':walls,'door':door_donor,'wall-donor':wall_donor,'door-prepare':door_prepare,'wall-prepare':wall_prepare}[sys.argv[1]]()
