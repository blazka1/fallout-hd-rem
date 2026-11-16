"""Guarded, backed-up installation of this component only."""
from pathlib import Path
import json,hashlib,shutil,sys,struct
from PIL import Image
from bake import R,W,O,D,B,read,save
BACK=R/'build/backups/before-wall-geometry-live-20261115'
PKG=R/'assets/hd/v13ent/wall-geometry-v2'
LIVE=R/'runtime/hd-world-pilot'
SRC=R/'work/hd-world-pilot/fallout1-ce-main'
SHARED=R/'build/hd-world-pilot/msvc/RelWithDebInfo'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(R)).replace('\\','/')
def changed_names():
 return [r['file'] for r in read(O/'placements.json')['placements']]+['wall-geometry.tsv','vault-rock-a.rgba','asset-061.rgba','asset-062.rgba','asset-063.rgba']+[f'tile-{i:03}-v{v}.rgba' for i in [62,63] for v in [1,2,3]]
def prepare_sources():
 assert read(B/'occlusion-final/result.json')['failed']==0
 assert not (BACK/'state.json').exists(),'Backup already exists; inspect before resuming'
 baseline=read(W/'source-baseline.json')
 for f,h in baseline.items():assert sha(SRC/f)==h,('Shared source changed',f)
 sources=list(baseline)+['src/game/hd_wall_geometry.inc','src/game/hd_wall_geometry_test.inc']
 for f in sources:
  if f not in baseline:assert not (SRC/f).exists()
 paths=[SRC/f for f in sources]+[LIVE/'fallout-ce.exe',LIVE/'data/art/hd/world-pilot/manifest.json']+[LIVE/'data/art/hd/world-pilot'/f for f in changed_names()]+[SHARED/'fallout-ce.exe',SHARED/'fallout-ce.pdb']
 files=[]
 for p in paths:
  exists=p.exists();item=dict(path=rel(p),existed=exists,before_sha256=sha(p) if exists else None)
  if exists:
   dest=BACK/rel(p);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  files.append(item)
 save(BACK/'state.json',dict(status='backed up before source integration',files=files,sources=sources))
 save(BACK/'runtime-before.json',{rel(p):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log'] and p.name.lower() not in ['debug.log','error.log']})
 for f in sources:shutil.copy2(W/'source'/f,SRC/f)
 print('Shared sources integrated with verified baseline and backups')
def install():
 final=read(B/'final-performance/result.json');assert final['failed']==0 and final['passed']>=1119
 state=read(BACK/'state.json')
 assert sha(SHARED/'fallout-ce.exe')==sha(W/'runtime/fallout-ce.exe')
 assert read(B/'final-performance/manifest.json')['executable_sha256'].lower()==sha(SHARED/'fallout-ce.exe'),'Final tested EXE must be installed'
 assert read(B/'benchmark-final/manifest.json')['executable_sha256'].lower()==sha(SHARED/'fallout-ce.exe')
 assert read(B/'benchmark-final/benchmark.json')['failed']==0
 for f in state['sources']:assert sha(SRC/f)==sha(W/'source'/f),('Shared source changed after testing',f)
 for item in state['files']:
  p=R/item['path']
  if str(p).startswith(str(SRC)) or str(p).startswith(str(SHARED)):continue
  assert (sha(p) if p.exists() else None)==item['before_sha256'],('Shared runtime changed',p)
 PKG.mkdir(parents=True,exist_ok=True);assets=[]
 for name in changed_names():
  source=D/name
  if name.endswith('.rgba'):
   raw=source.read_bytes();magic,version,w,h,c=struct.unpack('<4sIIII',raw[:20]);assert (magic,version,c)==(b'F1HD',1,4)
   png=PKG/(Path(name).stem+'.png');Image.frombytes('RGBA',(w,h),raw[20:]).save(png)
   assets.append(dict(runtime_file=name,runtime_sha256=sha(source),png=rel(png),png_sha256=sha(png),size=[w,h]))
  shutil.copy2(source,LIVE/'data/art/hd/world-pilot'/name)
 shutil.copy2(O/'relief-atlas.png',PKG/'relief-atlas-source.png')
 shutil.copy2(O/'generation.json',PKG/'generation.json')
 shutil.copy2(O/'placements.json',PKG/'registration.json')
 m=read(LIVE/'data/art/hd/world-pilot/manifest.json');byfile={a['runtime_file']:a for a in assets}
 for a in m['assets']:
  if a['filename'] in byfile:
   n=byfile[a['filename']];a['runtime_file_sha256']=n['runtime_sha256'];a['source_png']=str(R/n['png']);a['source_png_sha256']=n['png_sha256']
   a['appearance_component']='wall-geometry-v2';a['decoded_rgba_sha256']=hashlib.sha256((D/a['filename']).read_bytes()[20:]).hexdigest()
 m['wall_geometry']=dict(component='wall-geometry-v2',additional_placement_images=417,resource_types=62,approved_door_contour_preserved=True,geometry_only=True,registry='wall-geometry.tsv',registry_sha256=sha(D/'wall-geometry.tsv'),package=rel(PKG),report=rel(B/'final-performance/manifest.json'))
 save(LIVE/'data/art/hd/world-pilot/manifest.json',m)
 shutil.copy2(SHARED/'fallout-ce.exe',LIVE/'fallout-ce.exe')
 for item in state['files']:
  p=R/item['path'];item['installed_sha256']=sha(p) if p.exists() else None
 state['status']='installed';save(BACK/'state.json',state)
 changed={item['path'] for item in state['files']};protected=0
 for path,h in read(BACK/'runtime-before.json').items():
  if path not in changed:assert sha(R/path)==h,('Unexpected runtime modification',path);protected+=1
 for a in assets:assert sha(LIVE/'data/art/hd/world-pilot'/a['runtime_file'])==a['runtime_sha256']
 receipt=dict(status='installed-and-verified',runtime=rel(LIVE),executable_sha256=sha(LIVE/'fallout-ce.exe'),registered_wall_placements=417,door_contour_preserved=True,render_images=len(assets),source_types=62,assets=assets,checks=final,asset_audit=read(B/'asset-audit.json'),performance=read(B/'performance-comparison.json'),cache_image_comparison=read(B/'cache-image-comparison.json'),protected_runtime_files=protected,backup=rel(BACK),AGENTS_modified=False,geometry_only=True)
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='assets'})
 print('INSTALLED',len(assets),'images,',final['passed'],'PASS; protected',protected,'runtime files')
if __name__=='__main__':
 {'sources':prepare_sources,'install':install}[sys.argv[1]]()
