"""Two original-Qwen texture retention trials in an isolated CE runtime."""
from pathlib import Path
import importlib.util,json,sys,shutil,struct,uuid
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('wall_helpers',R/'work/hd-cave-wall-variety-20261115/pipeline.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);p=w.p
OUT=R/'assets/generated/v13ent-wall-texture-trials/v1-20261115';p.OUT=OUT
B=R/'build/hd-wall-texture-trials-20261115';LIVE=R/'runtime/hd-world-pilot'
RT=R/'work/hd-wall-texture-trials-20261115/runtime';DATA=RT/'data/art/hd/world-pilot'
POS={186:(120,640,102),189:(121,672,102),122:(122,704,102),123:(123,736,102),197:(130,768,103)}
def setup():
 if (OUT/'baseline.json').exists():return
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'inputs').mkdir(exist_ok=True)
 p.save(OUT/'baseline.json',{str(f.relative_to(R)):p.sha(f) for f in LIVE.rglob('*') if f.is_file()})
 RT.mkdir(parents=True,exist_ok=True)
 for f in LIVE.iterdir():
  if f.is_file() and (f.name in ['fallout-ce.exe','fallout.cfg','f1_res.ini'] or f.suffix.lower()=='.dll'):shutil.copy2(f,RT/f.name)
 shutil.copytree(LIVE/'data',RT/'data',ignore=shutil.ignore_patterns('SAVEGAME','savegame'),dirs_exist_ok=False)
 byid={a['asset_id']:a for a in p.read(DATA/'manifest.json')['assets']}
 rows=[];plan=p.read(w.OUT/'plan.json')
 for id,(base,x,y) in POS.items():
  a=byid[id];src=byid[base]['original_resource'];c=next(c for c in plan['contexts'] if any(s['source']==src for s in c['selected']))
  s=next(s for s in c['selected'] if s['source']==src)
  w.decode(DATA/a['filename']).save(OUT/'inputs'/('asset-%03d.png'%id))
  shutil.copy2(DATA/a['filename'],OUT/'inputs'/a['filename'])
  rows.append(dict(id=id,base=base,file=a['filename'],width=a['width'],height=a['height'],context=c['id'],
   donor_crop=[(s['x']-c['box_native'][0])*4,(s['y']-c['box_native'][1])*4,s['width']*4,s['height']*4],scene_crop=[(x-600)*4,(y-40)*4]))
 p.save(OUT/'inventory.json',rows)
 print('Isolated current runtime, including recent floor/cutaway changes; live files untouched',flush=True)
def generate():
 d=OUT/'comfy-retention'
 if (d/'run.json').exists():p.execute(d,{},{});return
 owners=np.fromfile(B/'current/owners.bin',np.uint32).reshape(540,960)[40:256,600:840]>>24
 mask=np.isin(owners,list(POS)).astype(np.uint8)*255
 Image.fromarray(np.repeat(np.repeat(mask,4,axis=0),4,axis=1)).save(OUT/'inputs/ownership.png')
 g={};outputs={};prefix='fallout1_wall_texture_trial/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return[k,0]
 def load(f):return add('LoadImage',image=p.upload(f))
 def mul(a,b):return add('MaskComposite',destination=a,source=b,x=0,y=0,operation='multiply')
 owned=add('ImageToMask',image=load(OUT/'inputs/ownership.png'),channel='red')
 interior=add('GrowMask',mask=owned,expand=-5,tapered_corners=True)
 soft=add('ImageBlur',image=add('MaskToImage',mask=interior),blur_radius=4,sigma=2.)
 owned=mul(owned,add('ImageToMask',image=soft,channel='red'))
 full=add('SolidMask',value=0.,width=960,height=864)
 band=add('SolidMask',value=1.,width=664,height=412)
 band=add('FeatherMask',mask=band,left=32,top=112,right=40,bottom=64)
 full=add('MaskComposite',destination=full,source=band,x=160,y=296,operation='add')
 full=add('MaskToImage',mask=mul(full,owned));donors={}
 for a in p.read(OUT/'inventory.json'):
  c=a['context']
  if c not in donors:
   raw=load(w.OUT/'qwen/material'/c/'raw.png')
   raw=add('ImageScale',image=raw,upscale_method='lanczos',width=2400,height=1600,crop='disabled')
   # Neutralize small color cast without the old brightness normalization.
   reg=p.read(w.OUT/'prepared/material-v2'/c/'registration.json');gain=np.array(reg['gain']);gain=np.rint(gain/gain.max()*255).astype(int)
   color=int(gain[0]*65536+gain[1]*256+gain[2]);flat=add('EmptyImage',width=2400,height=1600,batch_size=1,color=color)
   donors[c]=add('ImageBlend',image1=raw,image2=flat,blend_factor=1.,blend_mode='multiply')
  dx,dy,ww,hh=a['donor_crop'];sx,sy=a['scene_crop']
  crop=add('ImageCrop',image=donors[c],x=dx,y=dy,width=ww,height=hh)
  mask=add('ImageToMask',image=add('ImageCrop',image=full,x=sx,y=sy,width=ww,height=hh),channel='red')
  old=load(OUT/'inputs'/('asset-%03d.png'%a['id']))
  for name,strength in [('balanced',.60),('expressive',.95)]:
   amount=mul(mask,add('SolidMask',value=strength,width=ww,height=hh))
   result=add('ImageCompositeMasked',destination=old,source=crop,x=0,y=0,resize_source=False,mask=amount)
   result=add('JoinImageWithAlpha',image=result,alpha=[old[0],1])
   saved=add('SaveImage',images=result,filename_prefix=prefix+'/'+name+'/asset-%03d'%a['id']);outputs[saved[0]]=name+'/asset-%03d.png'%a['id']
 p.execute(d,g,outputs)
def stage(name):
 for a in p.read(OUT/'inventory.json'):
  old=np.array(Image.open(OUT/'inputs'/('asset-%03d.png'%a['id'])).convert('RGBA'))
  im=Image.open(OUT/'comfy-retention'/name/('asset-%03d.png'%a['id'])).convert('RGBA');new=np.array(im)
  assert np.array_equal(old[:,:,3],new[:,:,3]) and np.array_equal(old[:44],new[:44])
  (DATA/a['file']).write_bytes(struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes())
 print('Staged in isolated runtime:',name,flush=True)
def review():
 d=B/'review';d.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
 box=(1240,160,1640,570);sheet=Image.new('RGB',(1200,450),(24,27,27));dr=ImageDraw.Draw(sheet)
 baseline=np.array(Image.open(B/'current/entrance-hd.png').convert('RGB'));owners=np.fromfile(B/'current/owners.bin',np.uint32).reshape(540,960)>>24
 mask=np.repeat(np.repeat(np.isin(owners,list(POS)),2,axis=0),2,axis=1);qa=[]
 for i,(name,label) in enumerate([('current','Сейчас'),('balanced','Умеренная фактура'),('expressive','Выразительная фактура')]):
  shot=Image.open(B/name/'entrance-hd.png').convert('RGB');sheet.paste(shot.crop(box),(i*400,40));dr.text((i*400+10,8),label,font=font,fill='white')
  arr=np.array(shot);diff=np.any(arr!=baseline,2);assert not (diff&~mask).any(),name
  qa.append(dict(variant=name,changed_pixels=int(diff.sum()),outside_target_pixels=int((diff&~mask).sum())))
 sheet.save(d/'comparison.png')
 for name in ['balanced','expressive']:
  pair=Image.new('RGB',(960,530),(24,27,27));draw=ImageDraw.Draw(pair);wide=(1200,110,1680,600)
  for i,(folder,label) in enumerate([('current','Сейчас'),(name,'Больше фактуры' if name=='expressive' else 'Умеренная фактура')]):
   pair.paste(Image.open(B/folder/'entrance-hd.png').crop(wide),(i*480,40));draw.text((i*480+10,8),label,font=font,fill='white')
  pair.save(d/(name+'-comparison.png'))
 for f,h in p.read(OUT/'baseline.json').items():assert p.sha(R/f)==h,'live runtime changed: '+f
 p.save(d/'manifest.json',dict(status='isolated in-engine comparisons; not installed in main pilot',qa=qa,live_runtime_unchanged=True,
  original_qwen_prompt='6d7884cb-beb9-46cb-b4a1-22ba4a9c3a92',textures_only=True,lighting_unchanged=True))
 print('Saved real renderer comparisons; main runtime verified unchanged',flush=True)
def finish():
 review();m=p.read(B/'expressive-verified/manifest.json');assert m['result']['failed']==0
 assert m['executable_sha256'].lower()==p.sha(RT/'fallout-ce.exe')
 assert np.array_equal(np.array(Image.open(B/'expressive/entrance-hd.png')),np.array(Image.open(B/'expressive-verified/entrance-hd.png')))
 previous=R/'build/hd-cave-floor-cutaway-20261115/world-final'
 assert np.array_equal(np.array(Image.open(B/'current/entrance-hd.png')),np.array(Image.open(previous/'entrance-hd.png')))
 # The reference 1080p capture is pixel-identical to the current baseline;
 # use its corresponding real 4K capture, with no image enhancement.
 box=(2560,440,3200,920);pair=Image.new('RGB',(1280,520),(24,27,27));font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24);dr=ImageDraw.Draw(pair)
 for i,(path,label) in enumerate([(previous/'entrance-hd-4k.png','Сейчас — игровой рендер 4K'),(B/'expressive-verified/entrance-hd-4k.png','Больше фактуры — тот же свет')]):
  pair.paste(Image.open(path).crop(box),(i*640,40));dr.text((i*640+12,8),label,font=font,fill='white')
 pair.save(B/'review/detail-4k-comparison.png')
 p.save(R/'work/hd-wall-texture-trials-20261115/task.json',dict(status='two isolated in-engine candidates; not installed',checks=m['result'],
  current_runtime_sha256=p.sha(LIVE/'fallout-ce.exe'),live_runtime_unchanged=True,lighting_unchanged=True,
  recommended='expressive',review=str((B/'review').relative_to(R)),candidate_runtime=str(RT.relative_to(R))))
 print('Validated expressive trial:',m['result']['passed'],'PASS, 0 FAIL; main pilot unchanged',flush=True)
if __name__=='__main__':
 command=sys.argv[1]
 if command=='stage':stage(sys.argv[2])
 else:{'setup':setup,'generate':generate,'review':review,'finish':finish}[command]()
