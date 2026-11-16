"""Targeted sidecar installation, backup verification, and final provenance."""
import subprocess,datetime,shutil,sys,json,hashlib
from pipeline import *
def idle():
 r=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name fallout-ce,fallout-floor-test,fallout-seam-test,fallout-terminal-test -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
 assert r.stdout.strip()=='0','Close Fallout before installing this component'
def baseline():return read(BACK/('install-baseline.json' if (BACK/'install-baseline.json').exists() else 'runtime-before.json'))
def reconcile():
 idle();old=read(BACK/'runtime-before.json');new={f:p.sha(R/f) for f in old};changed=[f for f in old if old[f]!=new[f]]
 allowed=['runtime/hd-world-pilot/fallout.cfg','runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json']
 allowed+=['runtime/hd-world-pilot/data/art/hd/world-pilot/'+name for name in ['asset-120.rgba','asset-121.rgba','asset-122.rgba','asset-123.rgba','asset-130.rgba']+['wall-accent-%d.rgba'%i for i in [186,187,188,189,190,191,197,198]]]
 assert set(changed)<=set(map(lambda x:str(Path(x)),allowed)),changed
 current=read(DATA/'manifest.json');assert current['component_patches'][-1]['component']=='wall-upper-join-v1'
 norm=lambda b:__import__('re').sub(rb'(?m)^splash=\d+',b'splash=0',b)
 assert norm((RT/'fallout.cfg').read_bytes())==norm((BACK/'runtime/hd-world-pilot/fallout.cfg').read_bytes())
 for a in read(OUT/'inventory.json'):assert p.sha(DATA/a['filename'])==a['sha256']
 for f in changed:
  d=BACK/'pre-install-state'/f;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/f,d)
 write(BACK/'concurrent-changes-preserved.json',dict(component='wall-upper-join-v1',files=changed,action='Preserve newer files and manifest; no rollback or modification'))
 write(BACK/'install-baseline.json',new)
 print('Preserved independently installed upper wall join; refreshed installation baseline')
def stage():
 idle();old=baseline()
 # Other component files must never be restored from our historical snapshot.
 for f in ['runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json']:
  assert p.sha(R/f)==old[str(Path(f))],f'Concurrent change: {f}'
 for f in PACK.glob('*.rgba'):shutil.copy2(f,DATA/f.name)
 shutil.copy2(PACK/'tile-variants.tsv',DATA/'tile-variants.tsv')
 print('Staged tile sidecars only; installed EXE remains unchanged')
def finish():
 idle();exe=R/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe';checksum=p.sha(exe)
 checks={}
 for name in ['world-final','terminal','menu','hud']:
  m=read(BUILD/name/'manifest.json');assert m['result']['failed']==0 and m['executable_sha256'].lower()==checksum
  checks[name]=m['result']
 fallback=read(BUILD/'fallback-summary.json');assert fallback['failed']==0 and fallback['executable_sha256']==checksum
 checks['fallbacks']=dict(passed=fallback['passed'],failed=0,cases=len(fallback['cases']))
 for group in ['floor','cutaway']:
  for a in read(PACK/(group+'-manifest.json')):assert p.sha(DATA/a['file'])==a['rgba_sha256']
 old=baseline();manifestpath=DATA/'manifest.json'
 assert p.sha(manifestpath)==old[str(manifestpath.relative_to(R))]
 assert p.sha(RT/'fallout-ce.exe')==old[str((RT/'fallout-ce.exe').relative_to(R))]
 # Account for actual independent changes without copying older assets back.
 changed=[f for f,h in old.items() if not (R/f).exists() or p.sha(R/f)!=h]
 assert not changed,('Existing protected files changed before final install',changed)
 shutil.copy2(exe,RT/'fallout-ce.exe')
 records=read(PACK/'floor-manifest.json')+read(PACK/'cutaway-manifest.json')
 m=read(manifestpath);m['tile_variant_image_count']=len(records)
 patch=dict(component='floor-cutaway-variety-v1',package=str(PACK.relative_to(R)),floor_bases=8,floor_additional_images=24,cutaway_original_types=2,cutaway_total_appearances=8,cutaway_additional_images=6,
  table_sha256=p.sha(DATA/'tile-variants.tsv'),source_pixels_unchanged=True,original_map_unchanged=True,selection='stable FID / square cell / elevation hash',owner_format='existing asset ID, appended atlas page texel',executable_sha256=checksum)
 m['component_patches'].append(patch);write(manifestpath,m)
 receipt=dict(status='installed-and-verified',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**patch,checks=checks,
  successful_checks=sum(v['passed'] for v in checks.values()),failed_checks=0,protected_existing_files_unchanged=len(old)-2,backup=str(BACK.relative_to(R)),review=str((BUILD/'review/index.html').relative_to(R)),AGENTS_modified=False,HD_TEXTURE_GUIDE_modified=False,
  config_and_saves_unchanged=True,render_tests='Functional regression and SDL render captures, not a complete game playthrough')
 write(BUILD/'integration.json',receipt);write(R/'work/hd-cave-floor-cutaway-20261115/task.json',receipt)
 # The installed executable is byte-identical to the one used by all checks.
 assert p.sha(RT/'fallout-ce.exe')==checksum
 print(json.dumps(dict(status=receipt['status'],new_images=30,checks=receipt['successful_checks'],failed=0)))
if __name__=='__main__':{'stage':stage,'finish':finish,'reconcile':reconcile}[sys.argv[1]]()
