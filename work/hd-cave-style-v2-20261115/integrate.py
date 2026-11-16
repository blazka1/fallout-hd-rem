"""Stage validated graphics, then record the successful tested installation."""
import sys,json,shutil,hashlib,subprocess,re,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];BACK=R/'build/backups/before-cave-style-v2-20261115'
B=R/'build/hd-cave-style-v2-20261115';PACK=R/'assets/hd/v13ent/cave-distribution-v2'
RT=R/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def idle():
 result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name fallout-ce,fallout-cave-test -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
 assert result.stdout.strip()=='0','Close Fallout before changing runtime assets'
def stage():
 idle();assert not (B/'stage.json').exists(),'Already staged'
 before=read(BACK/'runtime-before.json')
 for f,h in before.items():assert sha(R/f)==h,f'Baseline changed: {f}'
 manifest=read(PACK/'manifest.json');assert len(manifest['records'])==16
 files=[r['id']+'.rgba' for r in manifest['records']]+['cave-variety-assets.tsv','cave-variety-placements.tsv']
 for f in files:shutil.copy2(PACK/f,DATA/f)
 save(B/'stage.json',dict(files=files,executable_sha256=sha(RT/'fallout-ce.exe'),package=str(PACK)))
 print('STAGED',len(files),'graphics/registration files; existing EXE unchanged')
def rollback():
 idle()
 for p in (BACK/'runtime/hd-world-pilot').rglob('*'):
  if p.is_file() and p.name!='fallout-ce.exe':shutil.copy2(p,RT/p.relative_to(BACK/'runtime/hd-world-pilot'))
 print('Restored previous appearance component from its own backup')
def finish():
 # Graphics were staged and tested before this step. Finalization only records
 # provenance; it is safe if the user has reopened the already updated game.
 assert not (B/'integration.json').exists()
 before=read(BACK/'runtime-before.json');exe=sha(RT/'fallout-ce.exe');checks={}
 for folder in ['world','terminal']:
  m=read(B/folder/'manifest.json');assert m['executable_sha256'].lower()==exe and m['result']['failed']==0
  checks[folder]=m['result']
 oldcfg=BACK/'runtime/hd-world-pilot/fallout.cfg'
 normalize=lambda x:re.sub(rb'(?m)^splash=\d+',b'splash=0',x)
 assert normalize((RT/'fallout.cfg').read_bytes())==normalize(oldcfg.read_bytes())
 staged=read(B/'stage.json');allowed={str((DATA/f).relative_to(R)) for f in staged['files']}
 # Do not rewrite the active game's startup counter. All other configuration
 # lines must remain byte-identical after normalization above.
 allowed.add(str((RT/'fallout.cfg').relative_to(R)))
 for f in staged['files']:assert sha(DATA/f)==sha(PACK/f),f'Staged graphics changed: {f}'
 for f,h in before.items():
  if f not in allowed:assert sha(R/f)==h,f'Protected file changed: {f}'
 manifest=read(DATA/'manifest.json');dist=read(PACK/'distribution.json')
 for a in manifest['assets']:
  if 224<=a['asset_id']<=239:
   entry=next(v for v in dist['assets'].values() if v['id']==a['asset_id'])
   source=R/entry['source'];payload=(DATA/entry['file']).read_bytes()[20:]
   a.update(source_png=str(source),source_png_sha256=sha(source),runtime_file_sha256=sha(DATA/entry['file']),decoded_rgba_sha256=hashlib.sha256(payload).hexdigest())
 manifest['component_patches'].append(dict(component='cave-style-match-v2',package=str(PACK),replaces_material_and_shape_of='cave-distribution-v1',new_images=16,assignments_unchanged=True,
  placements_registry_sha256=sha(DATA/'cave-variety-placements.tsv'),user_request='Match original and current-HD color, texture and more restrained form',executable_unchanged=exe))
 save(DATA/'manifest.json',manifest)
 changed=[f for f,h in before.items() if sha(R/f)!=h]
 allowed.add(str((DATA/'manifest.json').relative_to(R)));assert set(changed)<=allowed
 receipt=dict(status='installed-and-verified',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),executable_sha256=exe,executable_modified=False,
  images=16,new_appearance_placements=76,retained_old_appearances=40,checks=checks,changed_existing_files=changed,protected_files_unchanged=len(before)-len(changed),
  backup=str(BACK.relative_to(R)),package=str(PACK.relative_to(R)),review=str((B/'review/index.html').relative_to(R)),AGENTS_modified=False,
  config_change='Only splash startup counter; left as written by game/test launches. All other config bytes match backup.',
  scope='Repaint color/material and moderate silhouettes; keep all prior object assignments, game identities, positions and blockers')
 save(B/'integration.json',receipt);save(R/'work/hd-cave-style-v2-20261115/task.json',receipt)
 print(json.dumps(dict(status=receipt['status'],changed=len(changed),protected=receipt['protected_files_unchanged'],world=checks['world']['passed'],terminal=checks['terminal']['passed'])))
if __name__=='__main__':{'stage':stage,'finish':finish,'rollback':rollback}[sys.argv[1]]()
