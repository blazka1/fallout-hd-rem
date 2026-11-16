from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,value):(ROOT/p).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exe='runtime/hd-world-pilot/fallout-ce.exe';exe_hash=sha(exe)
checks={}
for label,folder in [('skeleton_and_player','build/hd-door-skeleton/preview/v18-final'),
                     ('world','build/hd-door-skeleton/preview/world-regression-v18-final'),
                     ('missing_asset','build/hd-door-skeleton/fallback-v18/missing'),
                     ('corrupt_asset','build/hd-door-skeleton/fallback-v18/corrupt')]:
    result=read(folder+'/result.json');manifest=read(folder+'/manifest.json')
    assert result['failed']==0 and manifest['executable_sha256'].lower()==exe_hash
    checks[label]={'passed':result['passed'],'failed':0,'report':folder+'/manifest.json'}
menu=read('build/hd-door-skeleton/menu-regression-v18/manifest.json')
assert menu['failed']==0 and menu['passed']==139 and menu['executable_sha256'].lower()==exe_hash
checks['menu']={'passed':139,'failed':0,'report':'build/hd-door-skeleton/menu-regression-v18/manifest.json'}
preview='build/hd-door-skeleton/preview/v18-final'
image=Image.open(ROOT/preview/'skeleton-hd-cave-4k.png')
assert image.size==(3840,2160)
image.crop((1640,560,2340,1000)).save(ROOT/preview/'skeleton-at-door-detail.png')
package='assets/hd/v13ent-door-skeleton/v1-x4'
payload='runtime/hd-world-pilot/data/art/hd/v13bones/v13bones.rgba'
asset=read(package+'/manifest.json');assert sha(payload)==asset['rgba_sha256']
receipt={'version':'V18','completed_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Install user-selected matte-bones-v5 skeleton in original V13ENT container',
 'runtime':'runtime/hd-world-pilot','executable_sha256':exe_hash,
 'previous_receipt':'build/hd-player-male/integration-v1.json',
 'backup':'build/backups/before-v18-door-skeleton-20261113',
 'asset':asset,'runtime_skeleton_file':payload,'checks':checks,
 'checks_primary_passed':sum(checks[k]['passed'] for k in ['skeleton_and_player','world','menu']),
 'checks_failed':0,'preview':preview+'/skeleton-at-door-detail.png',
 'preview_provenance':{'source':preview+'/skeleton-hd-cave-4k.png','source_sha256':sha(preview+'/skeleton-hd-cave-4k.png'),'crop':[1640,560,2340,1000],'resized':False},
 'preserved':{'environment_images':206,'player_images':54,'container_inventory_entries':2,'object_tile':17488,'object_pid':211,'object_fid':113,'native_size':[67,41],'changed_placements':0,'created_game_objects':0},
 'fallback':'Missing or malformed sprite uses original FRM; validated in two fresh game processes',
 'configuration':'[remaster] hd_v13_skeleton=1; F11 switches complete HD layer',
 'limits':['Only original flat FID113/PID211 frame0 in V13ENT is covered','Rendering/collision/inventory snapshots tested; not a full playthrough'],
 'source_changes':{p:sha(p) for p in ['work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.cc','work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.h','work/hd-world-pilot/fallout1-ce-main/src/game/object.cc','work/hd-world-pilot/fallout1-ce-main/src/game/hd_player_test.cc','work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot_test.cc']}}
save('build/hd-door-skeleton/integration-v18.json',receipt)
save('build/hd-world-pilot/integration-manifest.json',receipt)
asset['installed']=True;asset['integration_receipt']='build/hd-door-skeleton/integration-v18.json'
save(package+'/manifest.json',asset)
save('runtime/hd-world-pilot/data/art/hd/v13bones/manifest.json',asset)
task=read('work/hd-world-pilot/task.json')
task.update(task='V18: HD door skeleton with original container preserved',date='2026-11-13',
 user_scope='Install selected Qwen matte-bones-v5 and show it beside the Vault13 door',
 status='V18 installed and verified: skeleton, V17 player and V16 environment retained',
 known_scope_exclusions='Only V13ENT skeleton item and male unarmed stand/walk are HD; other items/actions/HUD and inner rectangular door remain classic',
 final_report='build/hd-door-skeleton/integration-v18.json',final_preview=preview,
 executable_sha256=exe_hash,integration_receipt='build/hd-door-skeleton/integration-v18.json',
 performance_report=preview+'/timings.json',
 latest_asset_delta={'unchanged_environment_images':206,'unchanged_player_images':54,'new_item_images':1,'changed_placements':0,'game_objects_created':0},
 skeleton_package=package,skeleton_runtime_file=payload,skeleton_checks=checks)
save('work/hd-world-pilot/task.json',task)
print(json.dumps({'status':'V18 installed and verified','checks':checks,'preview':receipt['preview'],'executable_sha256':exe_hash},indent=2))
