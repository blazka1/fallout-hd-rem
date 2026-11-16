from pathlib import Path
import json,hashlib,argparse
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();profiles=parser.add_mutually_exclusive_group();profiles.add_argument('--classic-contrast',action='store_true');profiles.add_argument('--balanced',action='store_true');args=parser.parse_args()
version=22 if args.balanced else (21 if args.classic_contrast else 20)
previous_version=version-1
preview=f'build/hd-door-skeleton/preview/v{version}-shadow'
package='assets/hd/v13ent-door-skeleton/'+('v5-balanced-shadow-x4' if args.balanced else ('v4-classic-shadow-x4' if args.classic_contrast else 'v3-shadow-x4'))
previous_report=f'build/hd-door-skeleton/integration-v{previous_version}-shadow.json'
runtime='runtime/hd-world-pilot/data/art/hd/v13bones'
result=read(preview+'/result.json');test=read(preview+'/manifest.json')
assert result['failed']==0 and result['passed']==244
receipt=read(previous_report)
assert receipt['executable_sha256']==test['executable_sha256'].lower()==sha('runtime/hd-world-pilot/fallout-ce.exe')
asset=read(package+'/manifest.json');assert asset['rgba_sha256']==sha(runtime+'/v13bones.rgba')
frame=Image.open(ROOT/preview/'skeleton-hd-cave-4k.png');assert frame.size==(3840,2160)
crop=frame.crop((1640,560,2340,1000));crop.save(ROOT/preview/'skeleton-at-door-detail.png')
before=Image.open(ROOT/f'build/hd-door-skeleton/preview/v{previous_version}-shadow/skeleton-at-door-detail.png')
comparison=Image.new('RGB',(1400,480),(28,29,28));comparison.paste(before,(0,40));comparison.paste(crop,(700,40))
d=ImageDraw.Draw(comparison);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
d.text((15,5),'Прежняя тень',font=f,fill='white');d.text((715,5),'Средний вариант' if args.balanced else ('Контраст ближе к оригиналу' if args.classic_contrast else 'Темнее и шире снизу'),font=f,fill='white')
comparison.save(ROOT/preview/'before-after-at-door.png')
receipt.update(version=f'V{version}',completed_utc=datetime.now(timezone.utc).isoformat(),scope='Match original-style dark compact contact shadow using ComfyUI; opaque body pixels unchanged' if args.classic_contrast else 'Strengthen and widen soft shadow below the selected skeleton using ComfyUI; opaque body pixels unchanged',
 previous_receipt=previous_report,backup=f'build/backups/before-v{version}-skeleton-shadow-20261113',
 package=package,asset=asset,fresh_checks={'skeleton_and_player':{'passed':244,'failed':0,'report':preview+'/manifest.json'}},
 preview=preview+'/skeleton-at-door-detail.png',comparison=preview+'/before-after-at-door.png',
 preview_provenance={'source':preview+'/skeleton-hd-cave-4k.png','source_sha256':sha(preview+'/skeleton-hd-cave-4k.png'),'crop':[1640,560,2340,1000],'resized':False},
 limits=['No new diffusion; deterministic ComfyUI alpha underlay adjustment','No full gameplay walkthrough'])
report=f'build/hd-door-skeleton/integration-v{version}-shadow.json'
if args.balanced:receipt['scope']='Middle-ground shadow between V20 soft and V21 contrast: opacity60%, sigma1.95, offset5HDpx; opaque body pixels unchanged'
save(report,receipt);save('build/hd-world-pilot/integration-manifest.json',receipt)
asset.update(installed=True,integration_receipt=report);save(package+'/manifest.json',asset);save(runtime+'/manifest.json',asset)
task=read('work/hd-world-pilot/task.json');task.update(task=f'V{version}: revised contact shadow below the Vault13 skeleton',user_scope='Match the stronger contrast and defined shadow of the user original-game reference' if args.classic_contrast else 'Darken the shadow and widen it below the body',status=f'V{version} installed and verified; original opaque body pixels preserved',final_report=report,final_preview=preview,integration_receipt=report,skeleton_package=package,skeleton_checks=receipt['fresh_checks'],performance_report=preview+'/timings.json')
if args.balanced:task['user_scope']='Choose a middle-ground shadow between the previous soft and original-style high contrast variants'
save('work/hd-world-pilot/task.json',task)
print(json.dumps({'version':f'V{version}','passed':244,'failed':0,'preview':receipt['preview']}))
