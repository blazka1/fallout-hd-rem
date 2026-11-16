"""Install only the verified EXE and approved HUD package; preserve all other files."""
from pathlib import Path
import hashlib,json,os,shutil

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'build/hd-hud-shell-install-20261116'
LIVE=ROOT/'runtime/hd-world-pilot'
PACKAGE=ROOT/'assets/hd/hud-panel/seed-qwen-v1'
EXE=ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

before=read(REPORT/'before.json')
checks={name:read(REPORT/name/'verification.json') for name in ['final-v2','fallback-corrupt-v2','menu-v2']}
assert all(r['failed']==0 and r['exit_code']==0 for r in checks.values()),checks
assert all(r['sha256'].lower()==sha(EXE) for r in checks.values()),'Tested executable changed.'
world=read(REPORT/'world-preservation-final.json')
assert all(row['outside_hud_changed_pixels']==0 for row in world)
for row in before['runtime']:
    p=LIVE/row['path'];assert p.is_file() and sha(p)==row['sha256'],'Live runtime changed since baseline: '+str(p)
for row in read(ROOT/'build/hd-world-pilot/logs/source-hashes.json'):
    p=ROOT/'work/hd-world-pilot/fallout1-ce-main'/row['path']
    assert p.is_file() and sha(p)==row['sha256'].lower(),'Source changed after verified compilation: '+str(p)
dest=LIVE/'data/art/hd/hud-panel/shell-monitor.rgba'
assert not dest.exists(),'HUD destination already exists; inspect before replacing.'
dest.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(PACKAGE/'shell-monitor.rgba',dest)
temp=LIVE/'fallout-ce-hud-install.new'
assert not temp.exists()
shutil.copy2(EXE,temp)
os.replace(temp,LIVE/'fallout-ce.exe')
preserved=[]
for row in before['runtime']:
    if row['path']=='fallout-ce.exe':continue
    assert sha(LIVE/row['path'])==row['sha256'],row['path']
    preserved.append(row['path'])
result=dict(status='installed-and-verified',runtime=str(LIVE),launcher='Start-Fallout-HD-World-Pilot.cmd',
    executable_sha256=sha(LIVE/'fallout-ce.exe'),asset_sha256=sha(dest),asset=str(dest),
    source_png=str(PACKAGE/'shell-monitor.png'),label='SKILLDEX',
    previous_executable_sha256=next(x['sha256'] for x in before['runtime'] if x['path']=='fallout-ce.exe'),
    backup=before['backup'],preserved_runtime_files=len(preserved),changed_runtime_files=['fallout-ce.exe'],
    added_runtime_files=['data/art/hd/hud-panel/shell-monitor.rgba'],checks=checks,
    passed=sum(r['passed'] for r in checks.values()),failed=0,world_pixel_comparison=world)
(REPORT/'integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
task=read(Path(__file__).with_name('task.json'))
task.update(status='installed and verified in active world pilot',runtime_installed=True,
    installation_report=str(REPORT/'integration.json'),selected_package=str(PACKAGE),runtime_executable_sha256=result['executable_sha256'])
Path(__file__).with_name('task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ['status','passed','failed','preserved_runtime_files','executable_sha256']},ensure_ascii=False))
