"""Seeded placement of existing sprites on engine-verified reachable cave floor."""
from pathlib import Path
import csv, json, random, hashlib, shutil, collections
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'assets/hd/v13ent/v11-floor-decor-x4'
TARGET=ROOT/'assets/hd/v13ent/v12-scattered-decor-x4'
RUN=ROOT/'assets/generated/v13ent-floor-decor/scatter-v1-20261112'
LAYOUT=ROOT/'build/hd-world-pilot/preview/scattered-decor-v12-layout/walkable-layout.tsv'
SEED=12112026
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if TARGET.exists() or RUN.exists():raise SystemExit('Existing run preserved; use a new revision.')
rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(LAYOUT.open(),delimiter='\t')]
by_tile={r['tile']:r for r in rows}
rng=random.Random(SEED)
old=json.loads((SOURCE/'manifest.json').read_text())
placements=[p for p in old['decoration_placements'] if p['asset_id']!=243]
selected=[by_tile[p['tile']] for p in placements]
def distance(a,b):return ((a['x']-b['x'])**2+4*(a['y']-b['y'])**2)**.5
def bucket(r):return min(4,r['path_length']//17)
for asset,counts in [(240,[2,2,2,2,2]),(242,[3,3,4,3,1])]:
    for zone,count in enumerate(counts):
        needed=count-sum(p['asset_id']==asset and bucket(by_tile[p['tile']])==zone for p in placements)
        candidates=[r for r in rows if bucket(r)==zone and r['scenery_distance']>=(3 if asset==240 else 2)
            and (r['wall_distance']>=3 if asset==240 else 2<=r['wall_distance']<=3)]
        rng.shuffle(candidates)
        for r in candidates:
            if needed<=0:break
            if min(distance(r,s) for s in selected)<110:continue
            placements.append({'asset_id':asset,'tile':r['tile'],'elevation':0,'offset_x':0,
                'offset_y':13 if asset==240 else 0,'flat':asset==240,
                'note':'Seeded reachable-floor scatter; depth band '+str(zone)})
            selected.append(r);needed-=1
        if needed:raise RuntimeError(f'Insufficient spaced candidates for {asset} zone{zone}: {needed}')
RUN.mkdir(parents=True)
write(RUN/'placements.json',placements)
write(RUN/'run.json',{'seed':SEED,'method':'seeded shuffled candidates stratified into five path-distance bands; fixed TSV, no runtime RNG',
    'candidate_count':len(rows),'candidate_file':str(LAYOUT.relative_to(ROOT)),'candidate_sha256':sha(LAYOUT),
    'spacing':'110 logical pixels in metric sqrt(dx^2+4dy^2); bones wall>=3/scenery>=3 hex; mushrooms wall2..3/scenery>=2 hex',
    'retained_entrance_anchors':[p['tile'] for p in placements[:3]],
    'counts':dict(collections.Counter(p['asset_id'] for p in placements)),
    'removed_new_spires':True,'existing_original_stalagmites_unchanged':True,'art_processing':'none; exact existing PNG bytes'})
shutil.copytree(SOURCE,TARGET,ignore=shutil.ignore_patterns('stalagmites.png','stalagmites.metadata.json'))
old.update(version='v12-scattered-decor-x4',parent_package={'path':str((SOURCE/'manifest.json').relative_to(ROOT)),'sha256':sha(SOURCE/'manifest.json')},
    decoration_image_count=3,total_image_count=201,decoration_placements=placements,
    decorations=[d for d in old['decorations'] if d['asset_id']!=243],
    placement_run={'path':str((RUN/'run.json').relative_to(ROOT)),'sha256':sha(RUN/'run.json')})
write(TARGET/'manifest.json',old)
print(json.dumps({'placements':len(placements),'counts':dict(collections.Counter(p['asset_id'] for p in placements)),'seed':SEED}))
