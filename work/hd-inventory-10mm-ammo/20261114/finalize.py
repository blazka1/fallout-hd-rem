"""Record only fresh successful reports for the exact installed executable."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, difflib

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'build/hd-inventory-10mm-ammo'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

exe=ROOT/'runtime/hd-world-pilot/fallout-ce.exe';exe_hash=sha(exe)
assert sha(ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')==exe_hash
reports=[]
for key in ['jhp-loaded','ap-loaded','jhp-missing','ap-missing','jhp-corrupt','ap-corrupt','knife','pistol','knuckles']:
    path=OUT/'preview'/('final-'+key)/'manifest.json';m=read(path)
    assert m['executable_sha256'].upper()==exe_hash
    assert m['exit_code']==0 and m['result']['failed']==0 and m['result']['passed']>0
    if m['expected_loaded']:
        assert sha(Path(m['asset_path']))==m['asset_sha256'].upper()
    reports.append(dict(name=key,path=str(path.relative_to(ROOT)),passed=m['result']['passed'],failed=0,sha256=sha(path)))
for name,path in [('world',OUT/'world-regression/manifest.json'),('menu',OUT/'menu-regression/manifest.json')]:
    m=read(path)
    # Read these report layouts explicitly before finalizing; the assertions
    # below handle the two existing project report schemas.
    stored=m.get('executable_sha256') or m.get('exe_sha256')
    if stored is None:stored=m.get('executable',{}).get('sha256') if isinstance(m.get('executable'),dict) else None
    assert stored and stored.upper()==exe_hash,(name,m.keys())
    stats=m.get('result') or m.get('checks') or m.get('summary') or m
    assert stats and stats['failed']==0 and stats['passed']>0,(name,m.keys())
    reports.append(dict(name=name,path=str(path.relative_to(ROOT)),passed=stats['passed'],failed=0,sha256=sha(path)))
assets=[]
for key,pid in [('jhp',29),('ap',30)]:
    package=ROOT/f'assets/hd/inventory/10mm-{key}/v1';selected=package/'ammo.rgba'
    runtime=ROOT/f'runtime/hd-world-pilot/data/art/hd/inventory/10mm-{key}/ammo.rgba'
    assert sha(selected)==sha(runtime)
    assets.append(dict(pid=pid,package=str(package.relative_to(ROOT)),runtime=str(runtime.relative_to(ROOT)),sha256=sha(runtime)))
receipts=sorted((OUT/'installations').glob('*.json'));assert len(receipts)>=2
summary=dict(status='installed_and_verified',created_utc=datetime.now(timezone.utc).isoformat(),
    executable=str(exe.relative_to(ROOT)),executable_sha256=exe_hash,assets=assets,
    checks=reports,passed=sum(x['passed'] for x in reports),failed=0,
    installation_receipts=[str(p.relative_to(ROOT)) for p in receipts if read(p)['files'][0]['sha256'].upper()==exe_hash],
    visual_review='Original/Seed/Qwen, light and dark alpha backgrounds, and fresh SDL HUD/inventory/hand/drag captures at 1080p and 4K reviewed.',
    limitations='Automated rendering checks and capture review; not a complete combat, barter, container or save/load playthrough.',
    historical_reports='Earlier non-final preview folders used a previous executable or contained a test-scrolling failure. They are retained and excluded from this total.')
write(OUT/'integration.json',summary)
write(ROOT/'work/hd-inventory-10mm-ammo/task.json',summary)
base=ROOT/'build/backups/before-hd-10mm-ammo-source-20261114';code=ROOT/'work/hd-world-pilot/fallout1-ce-main/src/game';patch=[]
for name in ['hd_hud.cc','hd_hud_test.cc','inventry.cc']:
    patch+=list(difflib.unified_diff((base/name).read_text().splitlines(True),(code/name).read_text().splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(ROOT/'work/hd-inventory-10mm-ammo/source.patch').write_text(''.join(patch),encoding='utf-8')
shutil.copyfile(ROOT/'build/hd-world-pilot/logs/source-hashes.json',OUT/'verified-source-hashes.json')
print(json.dumps(dict(passed=summary['passed'],failed=0,executable_sha256=exe_hash),indent=2))
