"""Copy the v10 pack unchanged and add four render-only ComfyUI sprites."""
from pathlib import Path
import json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'assets/hd/v13ent/v10-neutral-cave-x4'
RUN=ROOT/'assets/generated/v13ent-floor-decor/integration-v1-20261112'
TARGET=ROOT/'assets/hd/v13ent/v11-floor-decor-x4'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if TARGET.exists(): raise SystemExit('Existing pack preserved')
shutil.copytree(SOURCE,TARGET)
manifest=json.loads((TARGET/'manifest.json').read_text(encoding='utf-8'))
manifest.update(version='v11-floor-decor-x4',status='candidate_integration_pending',integrated_in_ce=False,
    parent_package={'path':str(SOURCE.relative_to(ROOT)/'manifest.json'),'sha256':sha(SOURCE/'manifest.json')},
    decoration_image_count=4,total_image_count=202,decorations=[],
    decoration_placements=json.loads((RUN/'placements.json').read_text()))
(TARGET/'decor').mkdir()
for item in json.loads((RUN/'manifest.json').read_text())['entries']:
    png='decor/'+item['key']+'.png';metadata='decor/'+item['key']+'.metadata.json'
    shutil.copyfile(RUN/item['file'],TARGET/png)
    write(TARGET/metadata,dict(item,render_only=True,game_object=False,collision=False,
        registration='native pixel dimensions; tile center/bottom anchor plus placement offset',
        workflow=str(RUN.relative_to(ROOT)/'workflow.json')))
    manifest['decorations'].append(dict(asset_id=item['asset_id'],key=item['key'],native_dimensions=item['native_dimensions'],
        png=png,sha256=sha(TARGET/png),metadata=metadata,metadata_sha256=sha(TARGET/metadata)))
write(TARGET/'manifest.json',manifest)
print(TARGET)
