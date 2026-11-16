"""Shared neutral-grey correction; native alpha, registration and seams locked."""
from pathlib import Path
import sys,importlib.util,json,hashlib,shutil,struct,uuid,argparse
sys.dont_write_bytecode=True
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
OLD=R/'work/hd-wall-original-restore-20261116'
PREV=R/'assets/generated/v13ent-wall-original/seed-qwen-20261116'
O=R/'assets/generated/v13ent-wall-original/grey-match-20261116'
B=R/'build/hd-wall-grey-match-20261116'
PKG=R/'assets/hd/v13ent/original-seed-qwen-grey-v2'
LIVE=R/'runtime/hd-world-pilot';D=W/'runtime/data/art/hd/world-pilot'
spec=importlib.util.spec_from_file_location('original_restore',OLD/'pipeline.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
h=p.h;h.OUT=O;read=p.read;save=p.save;sha=p.sha;node=p.node;decode=p.decode;pack=p.pack

def prepare():
 if (O/'plan.json').exists():return
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 shutil.copytree(OLD/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True);shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 files={str(f.relative_to(LIVE)).replace('\\','/'):sha(f) for f in LIVE.rglob('*') if f.is_file() and f.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 prior=read(R/'assets/hd/v13ent/original-seed-qwen-v1/manifest.json')
 assert all(sha(LIVE/'data/art/hd/world-pilot'/a['file'])==a['sha256'] for a in prior['images'])
 assert prior['exe_sha256']==sha(LIVE/'fallout-ce.exe')
 same=all(sha(f)==sha(LIVE/'data/art'/f.relative_to(OLD/'runtime/data/art')) for f in (OLD/'runtime/data/art').rglob('*') if f.is_file() and f.name!='manifest.json')
 assert same,'Need a refreshed baseline capture for concurrent art changes'
 save(B/'before-provenance.json',dict(source='build/hd-wall-original-restore-20261116/after-v1',all_art_and_exe_identical=True))
 (W/'test.ps1').write_text((OLD/'test.ps1').read_text(encoding='utf-8-sig').replace(OLD.name,W.name),encoding='utf-8')
 validation=(OLD/'validate.ps1').read_text(encoding='utf-8-sig').replace("'work/hd-wall-original-restore-20261116'", "'work/hd-wall-grey-match-20261116'").replace("'build/hd-wall-original-restore-20261116/native-check'","'build/hd-wall-grey-match-20261116/after-v1'")
 (W/'validate.ps1').write_text(validation,encoding='utf-8')
 targets=read(PREV/'targets.json');save(O/'targets.json',targets)
 m=read(D/'manifest.json');byres={a.get('original_resource'):a for a in m['assets'] if a['asset_id']<175}
 sources=sorted({v['source'] for v in targets.values() if v['source'].startswith('art/walls/')});slots=[]
 for i,res in enumerate(sources+['door-clearance']):
  filename='vault-rock-a.rgba' if res=='door-clearance' else byres[res]['filename']
  a=decode(D/filename);source=O/'input-sprites'/(Path(filename).stem+'.png');source.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(a).save(source)
  crop=a[:480,:124] if res=='door-clearance' else a
  slots.append(dict(source=res,filename=filename,png=str(source.relative_to(R)),sha256=sha(source),atlas=f'walls-{i//8:02d}',x=(i%4)*160+8,y=((i%8)//4)*704+8,width=crop.shape[1],height=crop.shape[0]))
 panels=[]
 for name in sorted({s['atlas'] for s in slots}):
  a=Image.new('RGBA',(640,1408));ss=[s for s in slots if s['atlas']==name]
  for s in ss:a.paste(Image.open(R/s['png']).crop((0,0,s['width'],s['height'])),(s['x'],s['y']))
  dest=O/'inputs'/name/'original.png';dest.parent.mkdir(parents=True,exist_ok=True);a.save(dest);panels.append(dict(id=name,slots=ss))
 dest=O/'inputs/caps';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(PREV/'inputs/caps/original.png',dest/'original.png')
 shutil.copy2(PREV/'inputs/caps/original-canny.png',dest/'original-canny.png')
 caps=next(x for x in read(PREV/'plan.json')['panels'] if x['id']=='caps');cap=Image.new('RGBA',(1152,256))
 for s in caps['slots']:
  a=decode(D/byres[s['source']]['filename']);cap.paste(Image.fromarray(a),(s['x']*4,s['y']*4))
 cap.save(dest/'current.png')
 refs=Image.new('RGBA',(1024,768));selected=[11,12,13,14,15,6,7,8];metrics=[]
 for i,aid in enumerate(selected):
  item=next(a for a in m['assets'] if a['asset_id']==aid);a=decode(D/item['filename']);im=Image.fromarray(a);im.thumbnail((240,360));refs.paste(im,((i%4)*256,(i//4)*384))
  rgb=a[:,:,:3][a[:,:,3]>240];metrics.append(dict(asset_id=aid,file=item['filename'],sha256=sha(D/item['filename']),mean_rgb=rgb.mean(0).tolist(),median_luma=float(np.median(rgb@np.array([.2126,.7152,.0722])))))
 refs.save(O/'rock-reference.png');save(O/'reference-measurements.json',metrics)
 save(O/'plan.json',dict(component='original-seed-qwen-grey-v2',wall_panels=panels,caps=caps,wall_transform=dict(method='ComfyUI Rec709 grey + linear tone curve, shared for every wall and edge',gain=1.18,offset=4),original_alpha_preserved=True,registration_preserved=True,seed_correction_note='Fresh original cap SeedVR2 x4; grey reference into Qwen; old blue low-frequency color will not be reintroduced',prior_component='original-seed-qwen-v1'))
 save(W/'task.json',dict(status='preparing neutral grey match',installed=False))
 print('PREPARED 63 wall/door masters, 3 cap masters, 537 runtime targets',flush=True)

def grey_graph(path,gain=1.18,offset=4,prefix=None):
 g={'1':node('LoadImage',image=h.upload(path))}
 def add(kind,**kwargs):k=str(len(g)+1);g[k]=node(kind,**kwargs);return[k,0]
 channels=[]
 for channel in ['red','green','blue']:channels.append(add('MaskToImage',mask=add('ImageToMask',image=['1',0],channel=channel)))
 rg=add('ImageBlend',image1=channels[0],image2=channels[1],blend_factor=.7152/(.2126+.7152),blend_mode='normal')
 y=add('ImageBlend',image1=rg,image2=channels[2],blend_factor=.0722,blend_mode='normal')
 factor=gain/(1-offset/255)
 bright=add('AdjustBrightness',images=y,factor=factor)
 if offset:
  size=Image.open(path).size;flat=add('EmptyImage',width=size[0],height=size[1],batch_size=1,color=offset*65793)
  bright=add('ImageBlend',image1=bright,image2=flat,blend_factor=1.,blend_mode='screen')
 out=add('SaveImage',images=bright,filename_prefix=prefix or 'fallout1_grey_match/'+uuid.uuid4().hex)
 return g,{out[0]:'grey.png'}

def colour():
 for panel in read(O/'plan.json')['wall_panels']:
  d=O/'colour'/panel['id']
  if (d/'result.json').exists():continue
  if (d/'run.json').exists():h.execute(d,{},{});continue
  g,outputs=grey_graph(O/'inputs'/panel['id']/'original.png');h.execute(d,g,outputs)
 d=O/'colour/caps-current'
 if not (d/'result.json').exists():
  g,outputs=grey_graph(O/'inputs/caps/current.png');h.execute(d,g,outputs)

def seed():
 h.seed(dict(id='caps'))
 d=O/'colour/caps-seed'
 if not (d/'result.json').exists():
  g,outputs=grey_graph(O/'seedvr2/caps/seedvr2-x4.png');h.execute(d,g,outputs)

def qwen():
 d=O/'qwen/caps'
 if (d/'result.json').exists():return
 if (d/'run.json').exists():h.execute(d,{},{});return
 prompt=('Restore these three exact original Fallout cave ceiling/cutaway rock tiles. The first image is the enlarged original layout. Recolor the stone to NEUTRAL CHARCOAL GREY, matching the neutral grey stone in the second reference. Remove all blue and cyan. Retain exactly the three diamonds, original positions, size, flat isometric projection, diagonal rock grain, existing crack directions and surface relief. Keep the existing dark shadow values readable, with restrained fine natural rock texture. Do not add rocks, holes, new cracks, facets, ledges, masonry or any raised geometry. No smooth plastic, gloss, color tint, text or extra objects. Black gaps between tiles remain empty. Match the modest contrast of the reference rocks; do not make the surface pale or silver.')
 g=read(PREV/'qwen/caps/prompt-api.json')
 g['1']['inputs']['image']=h.upload(O/'colour/caps-seed/grey.png')
 g['2']['inputs']['image']=h.upload(O/'inputs/caps/original-canny.png')
 g['8']['inputs']['prompt']=prompt
 # A compact material reference; output dimensions follow image_1 (1152x256).
 g['14']=node('LoadImage',image=h.upload(O/'rock-reference.png'))
 g['8']['inputs']['images.image_2']=['14',0]
 g['13']['inputs'].update(strength=1.0,end_percent=1.0)
 g['9']['inputs']['seed']=1611202602
 g['11']['inputs']['filename_prefix']='fallout1_grey_match/'+uuid.uuid4().hex+'/caps-qwen'
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
 h.execute(d,g,{'11':'raw.png'})

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage');args=a.parse_args()
 {'prepare':prepare,'colour':colour,'seed':seed,'qwen':qwen}[args.stage]()
