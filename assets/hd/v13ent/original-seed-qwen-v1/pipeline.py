"""Native cave geometry; conservative SeedVR2 -> Qwen 2.1 restoration."""
from pathlib import Path
import sys,json,hashlib,struct,shutil,importlib.util,uuid,argparse
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as nd
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-original/seed-qwen-20261116'
B=R/'build/hd-wall-original-restore-20261116'
PKG=R/'assets/hd/v13ent/original-seed-qwen-v1'
LIVE=R/'runtime/hd-world-pilot';D=W/'runtime/data/art/hd/world-pilot'
SRC=R/'assets/generated/v13ent-cave/v1-20261111/sources'
spec=importlib.util.spec_from_file_location('previous_pipeline',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.OUT=O
read=h.read;save=h.save;sha=h.sha;node=h.node
def decode(p):
 b=Path(p).read_bytes();m,v,w,hh,c=struct.unpack('<4sIIII',b[:20]);assert(m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(hh,w,4).copy()
def pack(p,a):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def prepare():
 if (O/'plan.json').exists():return
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 old=R/'work/hd-wall-blender-cave-20261115'
 shutil.copytree(old/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 (W/'test.ps1').write_text((old/'test.ps1').read_text(encoding='utf-8-sig').replace('hd-wall-blender-cave-20261115',W.name),encoding='utf-8')
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.bmp','.log']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 same=all(sha(p)==sha(LIVE/'data/art'/p.relative_to(old/'runtime/data/art')) for p in (old/'runtime/data/art').rglob('*') if p.is_file() and p.name!='manifest.json')
 assert same and sha(old/'runtime/fallout-ce.exe')==sha(LIVE/'fallout-ce.exe'),'Capture fresh baseline before continuing'
 save(B/'before-provenance.json',dict(source='build/hd-wall-blender-cave-20261115/after-v1',all_art_and_exe_identical=True))
 m=read(D/'manifest.json');sources={x['path']:x for x in read(SRC/'manifest.json')['assets']}
 base=[a for a in m['assets'] if a.get('original_resource','').startswith('art/walls/ca') and a['asset_id']<175]
 caps=[a for a in m['assets'] if a['asset_id'] in [61,62,63]]
 byid={a['asset_id']:a for a in base+caps};byfid={a['fid']:a for a in base}
 targets={a['filename']:dict(source=a['original_resource'],kind='base') for a in base+caps}
 for l in (D/'variants.tsv').read_text().splitlines():
  if not l or l.startswith('#'):continue
  v=l.split()
  if int(v[0]) in byid:targets[v[3]]=dict(source=byid[int(v[0])]['original_resource'],kind='variant')
 for l in (D/'wall-geometry.tsv').read_text().splitlines():
  if not l or l.startswith('#'):continue
  v=l.split();targets[v[10]]=dict(source=byfid[int(v[1])]['original_resource'],kind='placement',object=int(v[0]))
 targets['vault-rock-a.rgba']=dict(source='art/walls/ca036.frm',kind='door',object=252)
 for a in caps:
  for v in range(1,4):
   name=f"tile-{a['asset_id']:03d}-v{v}.rgba"
   if (D/name).exists():targets[name]=dict(source=a['original_resource'],kind='cap_variant')
 contexts=read(R/'assets/generated/v13ent-rock-detail/v1-crisp-20261112/analysis/context-plan.json')['contexts'];panels=[]
 for c in contexts:
  name=c['id'];d=O/'inputs'/name;d.mkdir(parents=True,exist_ok=True)
  shutil.copy2(R/f'assets/generated/v13ent-wall-joins/v1-20261112/prepared/{name}/original-context.png',d/'original.png')
  slots=[dict(source=s['source'],x=s['x']-c['box_native'][0],y=s['y']-c['box_native'][1],width=s['width'],height=s['height'],ownership_mask=s['ownership_mask']) for s in c['selected']]
  assert all(s['visible_fraction']==1 for s in c['selected'])
  panels.append(dict(id=name,native_size=[600,400],slots=slots,context=c))
 d=O/'inputs'/'caps';d.mkdir(parents=True,exist_ok=True);im=Image.new('RGBA',(288,64));slots=[]
 for i,a in enumerate(caps):
  s=sources[a['original_resource']];src=Image.open(SRC/s['rgba_png']).convert('RGBA');x=i*96+8;y=14
  im.paste(src,(x,y));slots.append(dict(source=s['path'],x=x,y=y,width=src.width,height=src.height))
 im.save(d/'original.png');panels.append(dict(id='caps',native_size=[288,64],slots=slots))
 records=[]
 for res in sorted({t['source'] for t in targets.values()}):
  s=sources[res];p=SRC/s['rgba_png'];assert sha(p)==s['rgba_png_sha256']
  dest=O/'originals'/(Path(res).name+'.png');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  records.append(dict(source=res,png=str(dest.relative_to(R)),sha256=sha(dest),size=[s['width'],s['height']],registration=s['registration']))
 save(O/'sources.json',records);save(O/'targets.json',targets)
 save(O/'plan.json',dict(pipeline='original FRM -> SeedVR2 x4 -> Qwen 2.1 conservative restoration, native alpha and registration',panels=panels,source_count=len(records),target_count=len(targets),blender_preserved='assets/hd/v13ent/blender-cave-v3',runtime_writes=False))
 save(W/'task.json',dict(status='preparing original restoration',installed=False))
 print('PREPARED',len(records),'native sources;',len(targets),'runtime image targets',flush=True)
def seed(name):
 p=next(p for p in read(O/'plan.json')['panels'] if p['id']==name);h.seed(p)
def qwen_input(name):
 d=O/'inputs'/name;src=Image.open(O/'seedvr2'/name/'seedvr2-x4.png').convert('RGB')
 if name=='caps':size=(1152,256);pad=0
 else:size=(1200,800);pad=8
 src=src.resize(size,Image.Resampling.LANCZOS)
 ref=Image.new('RGB',(size[0]+pad*2,size[1]));ref.paste(src,(pad,0));ref.save(d/'qwen-reference.png')
 # A geometric guide from the original: suppress one-pixel dither before edges.
 original=Image.open(d/'original.png').convert('RGB').resize(size,Image.Resampling.LANCZOS)
 smooth=Image.fromarray(np.rint(nd.gaussian_filter(np.array(original).astype(float),sigma=(1,1,0))).astype(np.uint8))
 control=Image.new('RGB',ref.size);control.paste(smooth,(pad,0));control.save(d/'original-control-input.png')
 dest=O/'controls'/name
 if not (dest/'result.json').exists():
  g={'1':node('LoadImage',image=h.upload(d/'original-control-input.png')),'2':node('Canny',image=['1',0],low_threshold=.14,high_threshold=.31),'3':node('SaveImage',images=['2',0],filename_prefix='fallout1_original_restore/control/'+uuid.uuid4().hex)}
  h.execute(dest,g,{'3':'original-canny.png'})
 shutil.copy2(dest/'original-canny.png',d/'original-canny.png')
 save(d/'sizing.json',dict(size=size,pad_left=pad,working=list(ref.size),control_source='original FRM, not generated image',canny=[.14,.31],gaussian_sigma=1.0))
def qwen(name):
 d=O/'qwen'/name
 if (d/'result.json').exists():return
 if (d/'run.json').exists():h.execute(d,{},{});return
 inp=O/'inputs'/name;assert(inp/'original-canny.png').exists()
 prompt=('Restore this exact late-1990s pre-rendered Fallout cave image at higher resolution. This is a faithful restoration, not a new design. Preserve every rock mass, major crack, silhouette, wall angle, wall height, top cut surface, contact point and existing seam. Preserve the original muted dark grey-brown colors, uneven natural stone and soft upper-left lighting. Gently recover small stone texture and readable chipped edges inside the existing forms. Keep the same contrast and shadow depths. No new cracks, new ledges, architectural slabs, brickwork, dramatic relief, polished surfaces, blue tint, moss, fungi or extra objects. Keep the black empty background exactly empty. ')
 prompt+=('These are three fixed-position original cutaway rock tiles; retain the flat diamond topology and the original very dark upper surface.' if name=='caps' else 'This is a connected wall neighborhood: all adjoining surfaces must remain continuous in their original geometry and lighting. Do not separate the wall into redesigned individual panels.')
 g={'1':node('LoadImage',image=h.upload(inp/'qwen-reference.png')),'2':node('LoadImage',image=h.upload(inp/'original-canny.png')),
 '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
 '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
 '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
 '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
 '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['1',0]}),
 '12':node('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'),
 '13':node('ZImageFunControlnet',model=['7',0],model_patch=['12',0],vae=['6',0],strength=0.9,image=['2',0],start_percent=0.0,end_percent=0.85),
 '9':node('KSampler',model=['13',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=16112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
 '10':node('VAEDecode',samples=['9',0],vae=['6',0]),
 '11':node('SaveImage',images=['10',0],filename_prefix='fallout1_original_restore/'+uuid.uuid4().hex+'/'+name)}
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');h.execute(d,g,{'11':'raw.png'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--only');a=p.parse_args()
 if a.stage=='prepare':prepare()
 else:
  for panel in read(O/'plan.json')['panels']:
   if a.only and panel['id']!=a.only:continue
   {'seed':seed,'qwen-input':qwen_input,'qwen':qwen}[a.stage](panel['id'])
