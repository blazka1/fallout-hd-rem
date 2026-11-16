"""Install only the 418 reviewed wall images and their component metadata."""
from bake_edges import *
import shutil
PKG=R/'assets/hd/v13ent/wall-edges-v3'
BACK=R/'build/backups/before-wall-edges-v3-20261115'
def main():
 baseline=read(W/'baseline.json');review=read(B/'comparison.json');test=read(B/'after-v2/manifest.json')
 assert test['result']['failed']==0 and test['result']['passed']==1119
 assert review['classic_all_exact']
 assert sha(R/'runtime/hd-world-pilot/fallout-ce.exe')==baseline['exe_sha256']==test['executable_sha256'].lower()
 assert not (BACK/'state.json').exists(),'An installation/backup already exists; inspect it'
 rows=read(O/'placements.json')['placements'];names=[r['file'] for r in rows]+['manifest.json']
 for r in rows:
  assert sha(LIVE/r['file'])==r['before_sha256']
  assert sha(D/r['file'])==r['sha256']
 # Concurrent work in any other asset must be incorporated and rechecked, not
 # silently overwritten by this package's older metadata.
 for rel,h in baseline['files'].items():
  if rel.startswith('data/art/') or rel=='fallout-ce.exe':assert sha(R/'runtime/hd-world-pilot'/rel)==h,('Runtime changed',rel)
 files=[];BACK.mkdir(parents=True)
 for name in names:
  p=LIVE/name;shutil.copy2(p,BACK/name);files.append(dict(name=name,before_sha256=sha(p)))
 save(BACK/'state.json',dict(status='backed up before asset installation',files=files))
 PKG.mkdir(parents=True,exist_ok=True)
 assets=[]
 for r in rows:
  png=R/r['png'];dest=PKG/png.name;shutil.copy2(png,dest);shutil.copy2(D/r['file'],LIVE/r['file'])
  assets.append(dict(runtime_file=r['file'],runtime_sha256=r['sha256'],png=str(dest.relative_to(R)),png_sha256=sha(dest),alpha_preserved=True,object_id=r['object']['id']))
 m=read(LIVE/'manifest.json');byfile={a['runtime_file']:a for a in assets}
 for a in m['assets']:
  if a['filename'] in byfile:
   n=byfile[a['filename']];a.update(runtime_file_sha256=n['runtime_sha256'],source_png=str(R/n['png']),source_png_sha256=n['png_sha256'],appearance_component='wall-edges-v3',decoded_rgba_sha256=hashlib.sha256((D/a['filename']).read_bytes()[20:]).hexdigest())
 m['wall_geometry'].update(component='wall-edges-v3',base_component='wall-geometry-v2',package=str(PKG.relative_to(R)),report=str((B/'after-v2/manifest.json').relative_to(R)),edge_images=418,alpha_preserved=True)
 save(LIVE/'manifest.json',m)
 for file in files:file['installed_sha256']=sha(LIVE/file['name'])
 save(BACK/'state.json',dict(status='installed',files=files))
 changed={'data/art/hd/world-pilot/'+n for n in names};protected=0
 for rel,h in baseline['files'].items():
  if rel not in changed:
   assert sha(R/'runtime/hd-world-pilot'/rel)==h,('Unexpected runtime modification',rel)
   protected+=1
 for a in assets:assert sha(LIVE/a['runtime_file'])==a['runtime_sha256']
 for src,name in [(O/'placements.json','registration.json'),(MASTER/'generation.json','generation.json'),(MASTER/'generation-prompt.txt','generation-prompt.txt'),(MASTER/'edge-guard-comfy/edge-relief-guarded.png','edge-relief-source.png')]:shutil.copy2(src,PKG/name)
 receipt=dict(status='installed and verified',component='wall-edges-v3',render_images=418,registered_wall_placements=417,approved_door_wall=1,source_types=62,assets=assets,checks=test['result'],comparison=review,audit=read(B/'asset-audit.json'),executable_changed=False,executable_sha256=baseline['exe_sha256'],other_runtime_files_unchanged=protected,backup=str(BACK.relative_to(R)),geometry_only=True)
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='assets'})
 print('INSTALLED 418 images; 1119 PASS; unchanged EXE and',protected,'other runtime files')
if __name__=='__main__':main()
