"""Verify complete x4 rat output and package/install only the isolated pilot."""
from pathlib import Path
import collections,hashlib,json,shutil,struct
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parents[2]
O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
P=R/'assets/hd/critter-rat/qwen21-seedvr2-v1-x4'
RT=R/'runtime/hd-rat-pilot'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
inv=read(O/'inventory.json');prepared={p.stem:p for p in (O/'prepared-v2').rglob('u*.png')}
selection=read(O/'selection.json') if (O/'selection.json').exists() else {}
for key,path in selection.get('images',{}).items():prepared[key]=O/path
assert len(prepared)==inv['unique_frames']==376,'Incomplete rat generation; nothing installed'
qa=read(O/'review/asset-qa.json');assert qa['prepared_unique']==376 and qa['failed']==0
assert not P.exists(),'Retain existing selected package'
frames=P/'frames';frames.mkdir(parents=True)
runtime=P/'runtime';runtime.mkdir()
records=[]
representatives={}
for r in inv['frames']:representatives.setdefault(r['unique'],r)
for key,r in representatives.items():
    path=prepared[key];im=Image.open(path).convert('RGBA')
    assert im.size==(r['width']*4,r['height']*4)
    expected=Image.open(O/'source/frames'/f'{key}.png').convert('RGBA').resize(im.size,Image.Resampling.NEAREST)
    assert np.array_equal(np.array(im)[:,:,3],np.array(expected)[:,:,3])
    shutil.copy2(path,frames/(key+'.png'))
    name='aimed.rgba' if r['code']=='na' else key+'.rgba'
    data=struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes()
    (runtime/name).write_bytes(data)
    assert (runtime/name).read_bytes()[20:]==Image.open(frames/(key+'.png')).convert('RGBA').tobytes()
    records.append(dict(id=key,source_dimensions=[r['width'],r['height']],dimensions=list(im.size),png=key+'.png',png_sha256=sha(frames/(key+'.png')),runtime_file=name,runtime_sha256=sha(runtime/name)))
lines=['# animation direction frame native_width native_height filename; original CE registration retained']
for r in inv['frames']:
    if r['animation']==64:continue
    lines.append(f'{r["animation"]}\t{r["direction"]}\t{r["frame"]}\t{r["width"]}\t{r["height"]}\t{r["unique"]}.rgba')
assert len(lines)==541
(runtime/'registry.tsv').write_text('\n'.join(lines)+'\n',encoding='utf-8')
provenance=[]
for stage in ['seed','qwen','prepared-v2','prepared-aimed-v3','prepared-aimed-v4']:
    for result in sorted((O/stage).glob('*/result.json')):
        job=read(result);provenance.append(dict(stage=stage,panel=result.parent.name,prompt_id=job['prompt_id'],elapsed_seconds=job['elapsed_seconds'],
            prompt_api=str((result.parent/'prompt-api.json').relative_to(R)).replace('\\','/'),prompt_api_sha256=sha(result.parent/'prompt-api.json'),
            workflow=str((result.parent/'workflow.json').relative_to(R)).replace('\\','/'),workflow_sha256=sha(result.parent/'workflow.json')))
manifest=dict(status='selected x4 rat package, isolated CE pilot',component='masrat ordinary cave rat',pid=0x01000030,art_index=24,
    source_files=64,directional_frames=546,world_animation_keys=540,aimed_diagram_keys=6,unique_images=376,
    scale=4,original_registration_retained=True,original_archives_modified=False,models=['Qwen Image 2.1 INT8 convrot','SeedVR2 3B INT8 convrot'],
    processing='SeedVR2 restoration, Qwen redraw, original thin borders and strict native-alpha registration retained through ComfyUI masks. PNG -> F1HD is byte-exact RGBA packing.',
    source_inventory=str((O/'inventory.json').relative_to(R)),source_inventory_sha256=sha(O/'inventory.json'),images=records,frames=inv['frames'],jobs=provenance,selection=selection,
    limitations=['Original binary native-pixel silhouette retained for all world frames; no change to gameplay geometry.',
        'Automatic generation is not a guarantee of perfect temporal coherence; inspect all provided animation previews.',
        'Other active cave work continues in its own runtime; this package is installed only in hd-rat-pilot.'])
(P/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
target=RT/'data/art/hd/critter-rat';assert not target.exists()
shutil.copytree(runtime,target)
for p in runtime.iterdir():assert sha(p)==sha(target/p.name)
shutil.copy2(R/'build/hd-rat-20261115/msvc/RelWithDebInfo/fallout-ce.exe',RT/'fallout-ce.exe')
print(json.dumps(dict(package=str(P),images=376,world_keys=540,runtime=str(RT),executable_sha256=sha(RT/'fallout-ce.exe'))),flush=True)
