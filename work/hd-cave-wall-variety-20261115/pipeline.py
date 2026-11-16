"""Coherent cave-wall material and restrained wall accents, existing Comfy stack."""
import sys,json,struct,hashlib,shutil,uuid,importlib.util
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cave_generation_helpers',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OLD=p.OUT;p.OUT=R/'assets/generated/v13ent-wall-variety/style-v1-20261115'
OUT=p.OUT;RT=R/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot'
CTX=R/'assets/generated/v13ent-rock-detail/v1-crisp-20261112/analysis/context-plan.json'
BACK=R/'build/backups/before-wall-variety-20261115'
NEW_SLOTS=[('ca011',1),('ca011',2),('ca013',1),('ca025',1),('ca025',2),('ca027',1),
 ('ca032',1),('ca032',2),('ca036',1),('ca036',2),('ca037',2),('ca038',1),
 ('ca038',2),('ca039',1),('ca039',2),('ca040',1),('ca041',1),('ca042',1),
 ('ca043',1),('ca044',1),('ca045',2),('ca046',1),('ca048',1),('ca048',2)]
def new_variants(walls):
 return [dict(base=walls['art/walls/'+stem+'.frm']['asset_id'],slot=slot,id=175+i,
  file='wall-accent-%03d.rgba'%(175+i),source=stem,theme=['cavities','cracks','moss','mushrooms'][i%4]) for i,(stem,slot) in enumerate(NEW_SLOTS)]

def decode(path):
 b=path.read_bytes();magic,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (magic,v,c)==(b'F1HD',1,4)
 return Image.frombytes('RGBA',(w,h),b[20:])
def prepare():
 if (OUT/'plan.json').exists():return
 OUT.mkdir(parents=True,exist_ok=True);BACK.mkdir(parents=True,exist_ok=True)
 runtime=p.read(DATA/'manifest.json');inventory=p.read(R/'assets/generated/v13ent-cave/v1-20261111/sources/manifest.json')['assets']
 source={a['path']:a for a in inventory};walls={a['original_resource']:a for a in runtime['assets'] if a.get('original_resource','').startswith('art/walls/ca') and a['asset_id']<175}
 assert len(walls)==62
 for res,a in walls.items():
  path=OUT/'inputs/walls'/(Path(res).stem+'.png');path.parent.mkdir(parents=True,exist_ok=True);decode(DATA/a['filename']).save(path)
  a['instances']=source[res]['map_instances']
 variants=[]
 for line in (DATA/'variants.tsv').read_text().splitlines():
  if line and not line.startswith('#'):
   base,slot,id,file=line.split();variants.append(dict(base=int(base),slot=int(slot),id=int(id),file=file))
   path=OUT/'inputs/old-variants'/(Path(file).stem+'.png');path.parent.mkdir(parents=True,exist_ok=True);decode(DATA/file).save(path)
 contexts=p.read(CTX)['contexts']
 for c in contexts:
  im=Image.new('RGB',(2400,1600));x0,y0,*_=c['box_native']
  for o in c['placements']:
   a=walls[o['source']];sprite=decode(DATA/a['filename']);im.paste(sprite,((o['x']-x0)*4,(o['y']-y0)*4),sprite)
  path=OUT/'inputs/contexts'/(c['id']+'.png');path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
 # Only exposed vertical faces, and only slots actually selected on this MAP.
 # Dark roof/back-face sprites ca053..ca070 are unsuitable for wall growth.
 new=new_variants(walls)
 assert max(a['id'] for a in new)==198
 filenames=[a['filename'] for a in walls.values()]+[a['file'] for a in variants]+['variants.tsv','manifest.json']
 for f in filenames:
  dest=BACK/'runtime/hd-world-pilot/data/art/hd/world-pilot'/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(DATA/f,dest)
 for f in ['fallout.cfg','fallout-ce.exe']:shutil.copy2(RT/f,BACK/'runtime/hd-world-pilot'/f)
 p.save(BACK/'runtime-before.json',{str(x.relative_to(R)):p.sha(x) for x in RT.rglob('*') if x.is_file() and x.suffix.lower()!='.log'})
 p.save(OUT/'plan.json',dict(walls=walls,contexts=contexts,old_variants=variants,new_variants=new,base_count=62,additional_variants=24,final_resource_count=246,
  source_exe=p.sha(RT/'fallout-ce.exe'),runtime_modified=False,scope='Coherent wall material, shallow cavities/cracks and rare moss/wall-adapted existing mushrooms; no game geometry changes'))
 p.save(R/'work/hd-cave-wall-variety-20261115/task.json',dict(status='prepared; material pilot next',output=str(OUT),backup=str(BACK),runtime_modified=False))
 print('Prepared 62 walls / 24 existing and 24 planned new variants',flush=True)

def wall(name):
 d=OUT/'qwen/material'/name
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 n=p.node;prefix='fallout1_wall_variety/'+uuid.uuid4().hex
 prompt='''Refine the rock MATERIAL of the first image, a continuous isometric Fallout cave wall neighborhood. The second image is the selected cave boulder MATERIAL reference: match its neutral charcoal-grey fractured stone, irregular laminar chips, crisp mineral edges and dark fissures. This must look like the SAME GEOLOGY and the SAME GAME ART, not a different environment.
Keep the FIRST image's exact camera, wall geometry, height, slope, contours, floor-contact line, wall joins and positions. Keep the black empty background exactly black. Preserve dark top cut faces and the existing large cracks and major strata positions. The wall remains one coherent connected surface, NOT separate columns or vertical tiled plates. Only change internal rock texture and small relief: sharper irregular stratified broken surfaces and readable medium-sized chips, with occasional calmer faces. Keep the current neutral grey color, brightness, lighting and moderate contrast. Do not brighten the wall or make it blue, pale, shiny, plastic, smooth clay, uniformly noisy or excessively sharp. No new large holes, doors, unsupported geometry, rocks on the floor, foliage, mushrooms, text or borders in this BASE material pass. Preserve the original composition meticulously. Texture changes should be clearly visible but restrained, compatible with neighboring original materials. No obvious repetitive grooves or regular bricks.'''
 g={'1':n('LoadImage',image=p.upload(OUT/'inputs/contexts'/(name+'.png'))),
 '2':n('ImageScale',image=['1',0],upscale_method='lanczos',width=1200,height=800,crop='disabled'),
 '3':n('LoadImage',image=p.upload(R/'assets/generated/v13ent-cave-variety/style-match-v2-20261115/selected/geo-rock-01.png')),
 '4':n('JoinImageWithAlpha',image=['3',0],alpha=['3',1]),
 '5':n('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
 '6':n('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
 '7':n('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
 '8':n('QwenImage21Cache',model=['5',0],device='cpu',dtype='default'),
 '9':n('TextEncodeQwenImage21',clip=['6',0],prompt=prompt,negative_prompt='',vae=['7',0],resolution=0,**{'images.image_1':['2',0],'images.image_2':['4',0]}),
 '10':n('KSampler',model=['8',0],positive=['9',0],negative=['9',1],latent_image=['9',2],seed=15119000+int(name[-2:]),steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.),
 '11':n('VAEDecode',samples=['10',0],vae=['7',0]),
 '12':n('SaveImage',images=['11',0],filename_prefix=prefix+'/'+name)}
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.execute(d,g,{'12':'raw.png'})

if __name__=='__main__':
 prepare()
 if len(sys.argv)>1 and sys.argv[1]!='prepare':
  for c in p.read(OUT/'plan.json')['contexts']:
   if sys.argv[1]=='all' or sys.argv[1]==c['id']:wall(c['id'])
