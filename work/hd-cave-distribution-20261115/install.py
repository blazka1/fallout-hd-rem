"""Install only the tested cave appearance component; preserve prior patches."""
from pathlib import Path
import hashlib, json, shutil, struct, datetime, subprocess, re
from PIL import Image

R=Path(__file__).resolve().parents[2]
B=R/'build/hd-cave-distribution-20261115'
BACK=R/'build/backups/before-cave-distribution-20261115'
RT=R/'runtime/hd-world-pilot'
PACK=R/'assets/hd/v13ent/cave-distribution-v1'
DATA=RT/'data/art/hd/world-pilot'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

assert not (B/'integration.json').exists(),'Installation receipt already exists'
running=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name fallout-ce,fallout-cave-test -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
assert running.stdout.strip()=='0','Close Fallout before installation'
baseline=read(BACK/'runtime-before.json')
exe=RT/'fallout-cave-test.exe';tested=sha(exe)
checks={}
for name in ['enabled-v3','disabled','fallback-missing','fallback-corrupt','terminal','benchmark-off','benchmark-on','menu']:
    m=read(B/name/'manifest.json');result=m.get('result',m)
    assert m['executable_sha256'].lower()==tested and result['failed']==0,name
    checks[name]=dict(passed=result['passed'],failed=0,manifest=str((B/name/'manifest.json').relative_to(R)))
frames=read(B/'disabled-baseline-comparison.json')
assert len(frames)==114 and all(x['exact'] for x in frames)
for path,h in baseline.items():
    if path.endswith('/fallout.cfg'): continue
    assert sha(R/path)==h.lower(),f'Protected baseline changed: {path}'
oldcfg=BACK/'runtime/hd-world-pilot/fallout.cfg'
assert re.sub(rb'(?m)^splash=\d+',b'splash=2',(RT/'fallout.cfg').read_bytes())==oldcfg.read_bytes(),'Unexpected config change'
dist=read(PACK/'distribution.json');manifest=read(DATA/'manifest.json');assets=[]
assert manifest['asset_count']==206 and len(manifest['assets'])==206
for name,a in dist['assets'].items():
    source=R/a['source'];rgba=Image.open(source).convert('RGBA').tobytes()
    packed=PACK/a['file'];assert packed.read_bytes()==struct.pack('<4sIIII',b'F1HD',1,512,512,4)+rgba
    assert sha(source)==a['sha256'] and sha(DATA/a['file'])==sha(packed)
    assets.append(dict(asset_id=a['id'],category='cave-instance-appearance',native_width=128,native_height=128,width=512,height=512,scale=4,
        filename=a['file'],source_png=str(source),source_png_sha256=sha(source),runtime_file='data/art/hd/world-pilot/'+a['file'],runtime_file_sha256=sha(packed),
        decoded_rgba_sha256=hashlib.sha256(rgba).hexdigest(),original_alpha_reused=False,placement_transform='cave-variety-placements.tsv; uniform fit and bottom contact'))
for file in ['cave-variety-assets.tsv','cave-variety-placements.tsv']:
    assert sha(PACK/file)==sha(DATA/file)
manifest['assets']+=assets;manifest['asset_count']=222
manifest['cave_appearance_image_count']=16
manifest['cave_appearance_placement_count']=76
manifest['component_patches'].append(dict(component='cave-distribution-v1',package=str(PACK),seed=dist['seed'],
    assets_registry='cave-variety-assets.tsv',assets_registry_sha256=sha(DATA/'cave-variety-assets.tsv'),
    placements_registry='cave-variety-placements.tsv',placements_registry_sha256=sha(DATA/'cave-variety-placements.tsv'),
    original_places=116,old_appearances=40,new_appearances=76,used_new_types=15,game_map_modified=False))
# All validation precedes the live EXE/manifest update. Test launch only changes splash.
shutil.copy2(oldcfg,RT/'fallout.cfg')
shutil.copy2(exe,RT/'fallout-ce.exe')
save(DATA/'manifest.json',manifest)
unchanged=[];changed=[]
for path,h in baseline.items():
    (unchanged if sha(R/path)==h.lower() else changed).append(path)
assert set(changed)=={'runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json'}
assert sha(RT/'fallout-ce.exe')==tested
for name in ['build-manifest.json','source-hashes.json']:
    shutil.copy2(R/'build/hd-world-pilot/logs'/name,B/('compiled-'+name))
receipt=dict(status='installed-and-verified-test-distribution',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    executable_sha256=tested,old_executable_sha256=baseline['runtime/hd-world-pilot/fallout-ce.exe'],runtime='runtime/hd-world-pilot',
    assignment_counts=dict(total=116,old=40,new=76,new_types=15,loaded_new_types=16,visible_new_placements_in_scan=70),checks=checks,
    exact_previous_hd_frames_with_component_disabled=114,protected_runtime_files_unchanged=len(unchanged),changed_existing_runtime_files=changed,
    added_component_files={str((DATA/a['filename']).relative_to(R)):sha(DATA/a['filename']) for a in assets},
    runtime_manifest_sha256=sha(DATA/'manifest.json'),config_preserved=True,AGENTS_modified=False,
    backup=str(BACK.relative_to(R)),review=str((B/'review/index.html').relative_to(R)),
    limits=['Automated renderer tests, not full playthrough or real save/load cycle','Six assigned places are occluded in the camera scan; all 15 used types are visible','Benchmark is hidden SDL CPU wall time, not gameplay FPS','New shapes retain their candidate surface material; this step tests distribution'])
save(B/'integration.json',receipt)
save(R/'work/hd-cave-distribution-20261115/task.json',receipt)
print(json.dumps(dict(status=receipt['status'],exe=tested,protected_files=len(unchanged),checks=checks),indent=2))
