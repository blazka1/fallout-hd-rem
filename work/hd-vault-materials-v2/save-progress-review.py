"""Audit installed art and export comparison figures without altering game assets."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-vault-surface-fixes-v4/progress-20261114';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
data=ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
m=read(data/'manifest.json');rows={r['asset_id']:r for r in m['assets']}
checks=[]
for r in read(ROOT/'assets/hd/v13ent/vault-materials-v2/manifest.json')['assets']:
 if r['asset_id']==16:continue
 p=data/f"asset-{r['asset_id']:03}.rgba";assert sha(p)==r['rgba_sha256'];checks.append(dict(asset_id=r['asset_id'],sha256=sha(p),package='vault-materials-v2'))
frame=read(ROOT/'assets/hd/v13ent/vault-surface-fixes-v4/manifest.json')
assert sha(data/'asset-016.rgba')==frame['rgba_sha256'];checks.append(dict(asset_id=16,sha256=frame['rgba_sha256'],package='vault-surface-fixes-v4'))
terminal=read(ROOT/'assets/hd/v13ent/terminal-detail-v5/manifest.json')
for state,name in [('off','asset-010.rgba'),('on','terminal-indicator-on.rgba')]:
 r=next(r for r in terminal['states'] if r['state']==state);assert sha(data/name)==r['rgba_sha256'];checks.append(dict(asset_id=10,state=state,sha256=r['rgba_sha256'],package='terminal-detail-v5'))
for r in checks:
 if r.get('state')=='on':continue
 assert rows[r['asset_id']]['runtime_file_sha256'].lower()==r['sha256']
exe=sha(ROOT/'runtime/hd-world-pilot/fallout-ce.exe');latest=read(ROOT/'build/hd-vault-surface-fixes-v4/integration.json');assert exe==latest['executable_sha256']
for kind in ['terminal','world']:
 r=read(ROOT/f'build/hd-vault-surface-fixes-v4/{kind}/manifest.json');assert r['executable_sha256'].lower()==exe and r['result']['failed']==0 and r['exit_code']==0
before_all=ROOT/'build/hd-terminal-indicator/halo-v4/loaded/terminal-on.png'
before_latest=ROOT/'build/hd-vault-clean-trim-v3/terminal/terminal-on.png'
after=ROOT/'build/hd-vault-surface-fixes-v4/terminal/terminal-on.png'
crop=(480,0,1200,420)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
figures=[]
for name,before,label in [('scene-before-after',before_all,'ДО — до обновления материалов и терминала'),('last-edits-before-after',before_latest,'ДО — перед последними правками рамы')]:
 canvas=Image.new('RGB',(1464,472),(25,25,25));d=ImageDraw.Draw(canvas)
 for x,title,path in [(8,label,before),(736,'ПОСЛЕ — текущее состояние',after)]:
  im=Image.open(path).convert('RGB');assert im.size==(1920,1080)
  d.text((x,12),title,font=font,fill=(232,232,232));canvas.paste(im.crop(crop),(x,46))
 dest=OUT/(name+'.png');canvas.save(dest)
 figures.append(dict(file=str(dest),before=str(before),before_sha256=sha(before),after=str(after),after_sha256=sha(after),crop=list(crop),resampling=False,lighting_or_color_edits=False))
report=dict(status='installed_files_verified',executable_sha256=exe,runtime_manifest_sha256=sha(data/'manifest.json'),selected_images_verified=len(checks),registered_base_assets=len(rows),images=checks,latest_test_passed=latest['total_passed'],latest_test_failed=latest['total_failed'],comparisons=figures)
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
backup=ROOT/'build/backups/before-agents-vault-progress-20261114';backup.mkdir(exist_ok=True)
assert not (backup/'AGENTS.md').exists();shutil.copy2(ROOT/'AGENTS.md',backup/'AGENTS.md')
print(json.dumps({k:report[k] for k in ['selected_images_verified','registered_base_assets','executable_sha256','latest_test_passed']}))
