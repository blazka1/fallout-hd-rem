from bake import *
import shutil
PKG=R/'assets/hd/v13ent/wall-crown-v4';BACK=R/'build/backups/before-wall-crown-v4-20261115'
def main():
 baseline=read(W/'baseline.json');review=read(B/'comparison.json');test=read(B/'after-v1/manifest.json')
 assert test['result']['failed']==0 and test['result']['passed']==1119 and review['classic_all_exact']
 assert sha(R/'runtime/hd-world-pilot/fallout-ce.exe')==baseline['exe_sha256']==test['executable_sha256'].lower()
 assert not (BACK/'state.json').exists(),'Existing installation must be inspected, not overwritten'
 rows=read(O/'placements.json')['images'];names=[r['file'] for r in rows]+['manifest.json']
 for r in rows:assert sha(LIVE/r['file'])==r['before_sha256'] and sha(D/r['file'])==r['sha256']
 for rel,h in baseline['files'].items():
  if rel.startswith('data/art/') or rel=='fallout-ce.exe':assert sha(R/'runtime/hd-world-pilot'/rel)==h,('Concurrent runtime change',rel)
 BACK.mkdir(parents=True);files=[]
 for name in names:
  shutil.copy2(LIVE/name,BACK/name);files.append(dict(name=name,before_sha256=sha(LIVE/name)))
 save(BACK/'state.json',dict(status='backed up before asset installation',files=files))
 PKG.mkdir(parents=True,exist_ok=True);assets=[]
 for r in rows:
  png=R/r['png'];dest=PKG/png.name;shutil.copy2(png,dest);shutil.copy2(D/r['file'],LIVE/r['file'])
  assets.append(dict(runtime_file=r['file'],runtime_sha256=r['sha256'],png=str(dest.relative_to(R)),png_sha256=sha(dest),alpha_preserved=True,kind=r['kind'],object_id=r.get('object',{}).get('id'),asset_id=r.get('asset_id')))
 m=read(LIVE/'manifest.json');byfile={a['runtime_file']:a for a in assets}
 for a in m['assets']:
  if a['filename'] in byfile:
   n=byfile[a['filename']];a.update(runtime_file_sha256=n['runtime_sha256'],source_png=str(R/n['png']),source_png_sha256=n['png_sha256'],appearance_component='wall-crown-v4',decoded_rgba_sha256=hashlib.sha256((D/a['filename']).read_bytes()[20:]).hexdigest())
 m['wall_geometry'].update(component='wall-crown-v4',base_component='wall-geometry-v2',package=str(PKG.relative_to(R)),report=str((B/'after-v1/manifest.json').relative_to(R)),geometry_only=False,material_preview=True,edge_images=418,cap_images=9,alpha_preserved=True)
 save(LIVE/'manifest.json',m)
 for f in files:f['installed_sha256']=sha(LIVE/f['name'])
 save(BACK/'state.json',dict(status='installed',files=files))
 changed={'data/art/hd/world-pilot/'+n for n in names};protected=0
 for rel,h in baseline['files'].items():
  if rel not in changed:assert sha(R/'runtime/hd-world-pilot'/rel)==h,('Unexpected modification',rel);protected+=1
 for a in assets:assert sha(LIVE/a['runtime_file'])==a['runtime_sha256']
 for src,name in [(O/'placements.json','registration.json'),(O/'generation.json','generation.json'),(O/'generation-prompts.txt','generation-prompts.txt'),(O/'wall-material.png','wall-material-source.png'),(O/'cap-seam-comfy/cap-periodic.png','cap-material-source.png')]:shutil.copy2(src,PKG/name)
 receipt=dict(status='installed and verified',component='wall-crown-v4',render_images=427,registered_wall_placements=417,approved_door_wall=1,cap_images=9,source_wall_types=62,assets=assets,checks=test['result'],comparison=review,audit=read(B/'asset-audit.json'),executable_changed=False,executable_sha256=baseline['exe_sha256'],other_runtime_files_unchanged=protected,backup=str(BACK.relative_to(R)),material_preview=True)
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='assets'})
 print('INSTALLED 427 images; 1119 PASS; unchanged EXE and',protected,'other runtime files')
if __name__=='__main__':main()
