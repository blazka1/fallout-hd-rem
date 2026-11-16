"""Record the asset-only V19 installation after the real CE preview passes."""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
preview='build/hd-door-skeleton/preview/v19-shadow'
package='assets/hd/v13ent-door-skeleton/v2-shadow-x4'
runtime='runtime/hd-world-pilot/data/art/hd/v13bones'
result=read(preview+'/result.json');test=read(preview+'/manifest.json')
assert result['failed']==0 and result['passed']==244
exe_hash=sha('runtime/hd-world-pilot/fallout-ce.exe')
assert test['executable_sha256'].lower()==exe_hash
prior=read('build/hd-door-skeleton/integration-v18.json')
assert prior['executable_sha256']==exe_hash,'Asset-only update must keep the tested executable'
asset=read(package+'/manifest.json')
assert sha(runtime+'/v13bones.rgba')==asset['rgba_sha256']
frame=Image.open(ROOT/preview/'skeleton-hd-cave-4k.png')
assert frame.size==(3840,2160)
crop=frame.crop((1640,560,2340,1000))
crop.save(ROOT/preview/'skeleton-at-door-detail.png')
before=Image.open(ROOT/'build/hd-door-skeleton/preview/v18-final/skeleton-at-door-detail.png')
comparison=Image.new('RGB',(1400,480),(28,29,28))
comparison.paste(before,(0,40));comparison.paste(crop,(700,40))
draw=ImageDraw.Draw(comparison);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
draw.text((15,5),'До',font=font,fill='white');draw.text((715,5),'С тенью Qwen',font=font,fill='white')
comparison.save(ROOT/preview/'before-after-at-door.png')
receipt={'version':'V19','completed_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Install user-selected Qwen contact-shadow-v6 skeleton; asset-only change',
 'runtime':'runtime/hd-world-pilot','executable_sha256':exe_hash,'executable_unchanged':True,
 'previous_receipt':'build/hd-door-skeleton/integration-v18.json',
 'backup':'build/backups/before-v19-skeleton-shadow-20261113',
 'package':package,'asset':asset,'runtime_skeleton_file':runtime+'/v13bones.rgba',
 'fresh_checks':{'skeleton_and_player':{'passed':244,'failed':0,'report':preview+'/manifest.json'}},
 'prior_engine_checks':'V18 world/menu/fallback checks retained as history, not rerun for this asset-only update',
 'preview':preview+'/skeleton-at-door-detail.png','comparison':preview+'/before-after-at-door.png',
 'preview_provenance':{'source':preview+'/skeleton-hd-cave-4k.png','source_sha256':sha(preview+'/skeleton-hd-cave-4k.png'),'crop':[1640,560,2340,1000],'resized':False},
 'preserved':prior['preserved'],
 'limits':['Qwen slightly changes fine bone/fabric detail as seen in the selected candidate','No full gameplay walkthrough']}
save('build/hd-door-skeleton/integration-v19-shadow.json',receipt)
save('build/hd-world-pilot/integration-manifest.json',receipt)
asset.update(installed=True,integration_receipt='build/hd-door-skeleton/integration-v19-shadow.json')
save(package+'/manifest.json',asset);save(runtime+'/manifest.json',asset)
task=read('work/hd-world-pilot/task.json')
task.update(task='V19: soft contact shadow under the Vault13 door skeleton',
 user_scope='Install Qwen shadow variant and inspect at the Vault13 door',
 status='V19 installed and verified; V18 executable, player and environment unchanged',
 final_report='build/hd-door-skeleton/integration-v19-shadow.json',final_preview=preview,
 integration_receipt='build/hd-door-skeleton/integration-v19-shadow.json',
 skeleton_package=package,skeleton_runtime_file=runtime+'/v13bones.rgba',
 skeleton_checks=receipt['fresh_checks'],performance_report=preview+'/timings.json',
 latest_asset_delta={'unchanged_environment_images':206,'unchanged_player_images':54,'replaced_item_images':1,'changed_placements':0,'game_objects_created':0})
save('work/hd-world-pilot/task.json',task)
print(json.dumps({'status':'V19 installed and verified','checks':receipt['fresh_checks'],'preview':receipt['preview']},indent=2))
