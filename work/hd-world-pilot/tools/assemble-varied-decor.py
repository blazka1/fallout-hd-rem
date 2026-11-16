"""Seven decorative images; exactly3 bone piles,14 mushroom groups and original litter."""
from pathlib import Path
import json,shutil,hashlib,random,collections
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'assets/hd/v13ent/v11-floor-decor-x4'
RUN=ROOT/'assets/generated/v13ent-floor-decor/variety-prepared-v1-20261112'
TARGET=ROOT/'assets/hd/v13ent/v13-varied-decor-x4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if TARGET.exists():raise SystemExit('Existing package preserved')
manifest=json.loads((SOURCE/'manifest.json').read_text())
prepared=json.loads((RUN/'manifest.json').read_text())['entries']
shutil.copytree(SOURCE,TARGET,ignore=shutil.ignore_patterns('stalagmites.png','stalagmites.metadata.json'))
manifest.update(version='v13-varied-decor-x4',decoration_image_count=7,total_image_count=205,
    parent_package={'path':str((SOURCE/'manifest.json').relative_to(ROOT)),'sha256':sha(SOURCE/'manifest.json')},
    decorations=[d for d in manifest['decorations'] if d['asset_id']!=243])
for item in prepared:
    png='decor/'+item['key']+'.png';meta='decor/'+item['key']+'.metadata.json'
    shutil.copyfile(RUN/item['file'],TARGET/png)
    write(TARGET/meta,dict(item,render_only=True,game_object=False,collision=False,
        registration='native tile center/bottom plus placement offsets',workflow=str((RUN/'workflow.json').relative_to(ROOT))))
    manifest['decorations'].append(dict(asset_id=item['asset_id'],key=item['key'],native_dimensions=item['native_dimensions'],
        png=png,sha256=sha(TARGET/png),metadata=meta,metadata_sha256=sha(TARGET/meta)))
sizes={d['asset_id']:d['native_dimensions'] for d in manifest['decorations']}
def place(asset,tile,flat):
    return dict(asset_id=asset,tile=tile,elevation=0,offset_x=0,offset_y=sizes[asset][1]//2 if flat else 0,flat=flat)
placements=[place(240,19491,True),place(241,18092,True),place(242,20087,False),
    place(244,24070,True),place(245,25729,True)]
# All positions passed actual renderer visibility + walking checks, except19488
# which passed those same checks as the former low stalagmite in V11.
mushroom_tiles=[20692,18689,17513,19910,18706,23079,25068,26067,19514,18714,25522,26338,19488]
variants=[242]*4+[246]*5+[247]*4
random.Random(12112026).shuffle(variants)
placements.extend(place(asset,tile,False) for asset,tile in zip(variants,mushroom_tiles))
assert collections.Counter(p['asset_id'] for p in placements)=={240:1,241:1,242:5,244:1,245:1,246:5,247:4}
write(RUN/'placements.json',placements)
manifest.update(decoration_placements=placements,placement_seed=12112026,
    placement_method='Seeded cave scatter filtered by actual visibility/walkover checks; fixed authored placements, no runtime RNG',
    decoration_density={'bone_piles':3,'mushroom_groups':14,'litter':1,'new_spires':0},
    source_run=str(RUN.relative_to(ROOT)))
write(TARGET/'manifest.json',manifest)
print('Selected205 images;3 different bone piles,14 mushroom groups across3 appearances,1 litter pile;no new spires')
