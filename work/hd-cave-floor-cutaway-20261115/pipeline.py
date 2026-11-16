"""Local Comfy material variants; Python only handles transport, QA and packing."""
from pathlib import Path
import sys, json, struct, hashlib, shutil, uuid, importlib.util
import numpy as np
from PIL import Image, ImageDraw
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cave_reference_pipeline',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OLD=p.OUT
OUT=R/'assets/generated/v13ent-floor-cutaway/variety-v1-20261115'
PACK=R/'assets/hd/v13ent/floor-cutaway-variety-v1'
BUILD=R/'build/hd-cave-floor-cutaway-20261115'
BACK=R/'build/backups/before-floor-cutaway-variety-20261115'
RT=R/'runtime/hd-world-pilot'
DATA=RT/'data/art/hd/world-pilot'
p.OUT=OUT
FLOORS=[1,34,35,36,47,51,53,56]
CUTAWAY=[62,63]
def write(path,value):p.save(path,value)
def read(path):return p.read(path)
def decode(path):
 b=path.read_bytes();magic,version,w,h,scale=struct.unpack('<4sIIII',b[:20]);assert magic==b'F1HD' and version==1 and scale==4
 return Image.frombytes('RGBA',(w,h),b[20:])
def setup():
 if (OUT/'inventory.json').exists():return
 OUT.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
 # Preserve all runtime state, and only the source files this component edits.
 tracked={}
 for f in RT.rglob('*'):
  if not f.is_file():continue
  tracked[str(f.relative_to(R))]=p.sha(f)
  if f.suffix.lower() not in ['.dat','.dll']:
   d=BACK/f.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 for name in ['hd_world_pilot.cc','hd_world_pilot.h','hd_world_pilot_test.cc','tile.cc','tile.h']:
  f=R/'work/hd-world-pilot/fallout1-ce-main/src/game'/name
  d=BACK/f.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 for name in ['AGENTS.md','HD-TEXTURE-GUIDE.md']:
  tracked[name]=p.sha(R/name)
 write(BACK/'runtime-before.json',tracked)
 records=[]
 for line in (DATA/'registry.tsv').read_text().splitlines():
  if not line or line.startswith('#'):continue
  t=line.split();aid=int(t[0])
  if aid not in FLOORS+CUTAWAY:continue
  im=decode(DATA/t[4]);path=OUT/'inputs'/f'base-{aid:03}.png';path.parent.mkdir(exist_ok=True);im.save(path)
  records.append(dict(id=aid,fid=int(t[1]),width=int(t[2]),height=int(t[3]),filename=t[4],sha256=p.sha(DATA/t[4]),input=str(path.relative_to(R)),group='floor' if aid in FLOORS else 'cutaway'))
 write(OUT/'inventory.json',records)
 # Literal contact sheet for inspection, not an artistic operation.
 sheet=Image.new('RGB',(640,10*170),(22,22,22));d=ImageDraw.Draw(sheet)
 for i,a in enumerate(records):
  im=Image.open(R/a['input']);sheet.paste(im,(0,i*170+22));d.text((0,i*170+3),f"{a['group']} ID{a['id']} tile {a['fid']&4095}",fill='white')
 sheet.save(OUT/'current-materials.png')
 print('Prepared baseline and 10 tile materials',flush=True)
def graph():
 g={};outputs={};prefix='fallout1_floor_cutaway_variety/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 def save(im,name):k=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 return g,outputs,add,load,save
def generate(group,index):
 dst=OUT/'qwen'/f'{group}-{index}'
 if (dst/'run.json').exists():return p.execute(dst,{}, {})
 g,outputs,add,load,save=graph()
 if group=='floor':
  ref=load(OLD/'inputs/floor/current-hd.png')
  second=load(OLD/'qwen/floor/a-full/raw.png')
  prompt='''Create ONE continuous rectangular 1024x768 orthographic ground MATERIAL TEXTURE for a Fallout 1 cave. Image 1 is the PRIMARY reference: match exactly its dark neutral charcoal-grey hue, irregular fine layered stone grain, densely chipped mineral texture, subdued brightness and pre-rendered isometric game style. Image 2 is ONLY a reference for varied natural cracks and small angular grit; do NOT copy its purple background, its floating tile shapes, bevels or borders. Fill the ENTIRE output with a single continuous flat cave floor surface, edge to edge, without margins. View and light direction must match Image 1, upper-left soft light, extremely low relief. Natural compact worn rocky earth with shallow irregular fractures and very sparse tiny angular fragments. Rich rough original-style mineral grain, medium sharp chipped edges, fine dusty granular detail. Keep nearly uniform low brightness across the whole image with no spotlight, no vignette, no large bright or black patches. Varied arrangement of small fractures and gravel at the same scale as Image 1. No artificial noise, no clay or plastic, no smooth polygon slabs, no deep craters, no enormous stones, no columns, vegetation, water, tiles, diamonds, detached islands, cast shadows, visible tile borders, text or purple. No perspective framing: this is a texture filling the entire rectangle, not an object on a background. '''
  prompt+=['Small shallow branching cracks over compact worn stone, restrained small grains with a few tiny loose chips.','Denser scattered fine angular gravel among irregular weathered flat stone chips, subtle shallow fissures.','Uneven thin fractured stone flakes mixed with fine dusty grit, subdued small pits and occasional tiny fragments.'][index-1]
 else:
  ref=load(OUT/'inputs/base-062.png');second=load(OUT/'inputs/base-063.png')
  prompt='''Create ONE continuous rectangular 640x320 rock MATERIAL TEXTURE for the dark upper CUTAWAY MASS of a classic Fallout 1 cave. The two images show the current neighboring cutaway tile textures. Match their EXACT very dark charcoal-grey palette, dense brittle layered rock grain, narrow irregular diagonal ridges running bottom-left to top-right, fine chipped striations, subtle upper-left light and tight texture scale. Preserve the same rich rough pre-rendered game material. Introduce natural non-repeating variations in the spacing, length, fracture branching and overlap of this small-scale rock grain. Very restrained broad value variation only, no focal features. This is an opaque continuous material filling the whole rectangle edge-to-edge. Keep the cutaway mass dark and visually subordinate to the cave wall. No floor slabs, large boulders, bricks, regular repeated diagonal lines, smooth clay, melted plastic, shiny wet surfaces, bright ridges, blue tint, holes, caves, plants, perspective framing, transparent space, background, borders, text or cast shadows. Do not enlarge the grain or turn this into a landscape or separate objects. '''
  prompt+=['Narrow fractured overlapping laminae, some interrupted at irregular lengths.','Slightly more broken chipped ridges with interlocking small cross-fractures.','Some ridges split into two thinner layers, scattered shallow pits between them.'][index-1]
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
 clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
 vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors');model=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 # Reference conditioning preserves reference dimensions; explicitly supply the
 # requested empty latent so texture sheets have a known, grid-aligned extent.
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':ref,'images.image_2':second})
 latent=add('EmptySD3LatentImage',width=1024 if group=='floor' else 640,height=768 if group=='floor' else 320,batch_size=1)
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=latent,seed=15121000+(0 if group=='floor' else 10)+index,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 result=add('VAEDecode',samples=sample,vae=vae);save(result,'raw')
 dst.mkdir(parents=True,exist_ok=True);(dst/'prompt.txt').write_text(prompt,encoding='utf-8');return p.execute(dst,g,outputs)
def prepared_dir(group):return OUT/'prepared'/('cutaway-v2' if group=='cutaway' else group)
def prepare(group):
 inventory=[a for a in read(OUT/'inventory.json') if a['group']==group]
 dst=prepared_dir(group)
 if (dst/'run.json').exists():return p.execute(dst,{}, {})
 g,outputs,add,load,save=graph();records=[]
 for a in inventory:
  aid=a['id'];baseim=np.array(Image.open(R/a['input']).convert('RGBA'));hh,ww=baseim.shape[:2]
  base=load(R/a['input'])
  # A three-native-pixel perimeter is exact, with a feathered inner transition.
  # All color, texture, mask and compositing operations execute in Comfy.
  mask=add('SolidMask',value=0.,width=ww,height=hh)
  inner=add('SolidMask',value=1.,width=ww-24,height=hh-24)
  feather=40 if group=='cutaway' else 20
  inner=add('FeatherMask',mask=inner,left=feather,top=feather,right=feather,bottom=feather)
  mask=add('MaskComposite',destination=mask,source=inner,x=12,y=12,operation='add')
  for slot in range(1,4):
   rawpath=OUT/'qwen'/f'{group}-{slot}'/'raw.png';rawim=np.array(Image.open(rawpath).convert('RGB'));rh,rw=rawim.shape[:2]
   raw=load(rawpath)
   if group=='cutaway':
    rw,rh=1280,640
    raw=add('ImageScale',image=raw,upscale_method='lanczos',width=rw,height=rh,crop='disabled')
   x=(aid*67+slot*113)%(rw-ww+1);y=(aid*29+slot*47)%(rh-hh+1)
   crop=add('ImageCrop',image=raw,x=x,y=y,width=ww,height=hh)
   actual=(rawim.mean(axis=(0,1)) if group=='cutaway' else rawim[y:y+hh,x:x+ww].mean(axis=(0,1)))
   target=baseim[:,:,:3][baseim[:,:,3]>200].mean(0)
   gain=np.rint(np.minimum(target/np.maximum(actual,1),1)*255).astype(int)
   lift=np.rint(np.clip((target-actual)/(255-actual),0,1)*255).astype(int)
   color=lambda v:int(v[0]*65536+v[1]*256+v[2])
   mul=add('EmptyImage',width=ww,height=hh,batch_size=1,color=color(gain))
   matched=add('ImageBlend',image1=crop,image2=mul,blend_factor=1.,blend_mode='multiply')
   scr=add('EmptyImage',width=ww,height=hh,batch_size=1,color=color(lift))
   matched=add('ImageBlend',image1=matched,image2=scr,blend_factor=1.,blend_mode='screen')
   if group=='cutaway':
    matched=add('ColorTransfer',image_target=crop,image_ref=base,method='histogram',source_stats='per_frame',strength=1.)
   # Retain substantial original grain; new differences are authored material,
   # never random noise, arbitrary brightness or rotated copies of a base tile.
   strength=(.72 if aid in [1,34,35,36] else .45) if group=='floor' else .75
   mixed=add('ImageBlend',image1=base,image2=matched,blend_factor=strength,blend_mode='normal')
   result=add('ImageCompositeMasked',destination=base,source=mixed,x=0,y=0,resize_source=False,mask=mask)
   result=add('JoinImageWithAlpha',image=result,alpha=[base[0],1])
   filename=f'tile-{aid:03}-v{slot}';save(result,filename)
   records.append(dict(base_id=aid,slot=slot,png=filename+'.png',file=filename+'.rgba',donor=str(rawpath.relative_to(R)),donor_sha256=p.sha(rawpath),crop=[x,y,ww,hh],target_mean=target.tolist(),raw_mean=actual.tolist(),exact_edge_hd_pixels=12,feather_hd_pixels=feather,color_method='histogram' if group=='cutaway' else 'multiply/screen',donor_scale=2 if group=='cutaway' else 1))
 write(dst/'records.json',records);p.execute(dst,g,outputs)
def package(group):
 PACK.mkdir(parents=True,exist_ok=True);records=read(prepared_dir(group)/'records.json');inventory={a['id']:a for a in read(OUT/'inventory.json')}
 for a in records:
  path=prepared_dir(group)/a['png'];im=Image.open(path).convert('RGBA');arr=np.array(im);base=np.array(Image.open(R/inventory[a['base_id']]['input']).convert('RGBA'))
  # Comfy alpha export may differ by one byte; this opaque tile family must be exact.
  assert np.array_equal(arr[:,:,3],base[:,:,3]),a
  edge=np.zeros(arr.shape[:2],bool);edge[:12]=1;edge[-12:]=1;edge[:,:12]=1;edge[:,-12:]=1
  assert np.array_equal(arr[edge],base[edge]),('edge',a)
  changed=np.any(arr[:,:,:3]!=base[:,:,:3],axis=2)
  assert changed.mean()>.25,('insufficient variation',a)
  (PACK/a['png']).write_bytes(path.read_bytes());(PACK/a['file']).write_bytes(struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes())
  a.update(source_png_sha256=p.sha(path),rgba_sha256=p.sha(PACK/a['file']),changed_fraction=float(changed.mean()),mean_rgb=arr[:,:,:3].mean((0,1)).tolist())
 write(PACK/(group+'-manifest.json'),records)
 rows=[]
 for kind in ['floor','cutaway']:
  if (PACK/(kind+'-manifest.json')).exists():
   rows.extend(f"{a['base_id']}\t{a['slot']}\t{a['file']}" for a in read(PACK/(kind+'-manifest.json')))
 (PACK/'tile-variants.tsv').write_text('# base_id slot(1..3) filename; exact base alpha and 12-HD-pixel perimeter\n'+'\n'.join(rows)+'\n',encoding='utf-8')
 print('Packaged',group,len(records),'variants',flush=True)
if __name__=='__main__':
 command=sys.argv[1];setup()
 if command=='setup':pass
 elif command=='generate':
  for i in range(1,4):generate(sys.argv[2],i)
 elif command=='prepare':prepare(sys.argv[2]);package(sys.argv[2])
