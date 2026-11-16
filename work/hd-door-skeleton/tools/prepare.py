from pathlib import Path
import sys,importlib.util,uuid,json,struct,hashlib,time,urllib.parse,argparse
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'assets/generated/v13ent-door-skeleton-qwen/game-prepared-v1-20261113'
PACK=ROOT/'assets/hd/v13ent-door-skeleton/v1-x4'
SOURCE=ROOT/'assets/generated/v13ent-door-skeleton-qwen/trial-v1-20261113/matte-bones-v5/qwen21-skeleton-raw.png'
parser=argparse.ArgumentParser(description='Prepare a selected RGBA skeleton using ComfyUI; no generation')
parser.add_argument('--source',type=Path,default=SOURCE)
parser.add_argument('--out',type=Path,default=RUN)
parser.add_argument('--package',type=Path,default=PACK)
args=parser.parse_args()
SOURCE=args.source.resolve();RUN=args.out.resolve();PACK=args.package.resolve()
for folder in (RUN,PACK):folder.relative_to(ROOT)
if (PACK/'manifest.json').exists():
    previous=json.loads((PACK/'manifest.json').read_text(encoding='utf-8-sig'))
    if previous.get('installed') or previous['source_sha256']!=hashlib.sha256(SOURCE.read_bytes()).hexdigest():
        raise SystemExit('Preserve existing selected package; choose a new package directory')
spec=importlib.util.spec_from_file_location('trial',ROOT/'assets/generated/v13ent-door-skeleton-qwen/trial-v1-20261113/run-qwen21-edit.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
BASE='http://127.0.0.1:8188'
RUN.mkdir(parents=True,exist_ok=True)
if (RUN/'run.json').exists():
    run=json.loads((RUN/'run.json').read_text());graph=json.loads((RUN/'prompt-api.json').read_text())
else:
    q.require_idle(BASE)
    token=uuid.uuid4().hex
    uploaded=q.upload(BASE,SOURCE,'game-bones-'+token+'.png')
    graph={'1':{'class_type':'LoadImage','inputs':{'image':uploaded}},
           '2':{'class_type':'JoinImageWithAlpha','inputs':{'image':['1',0],'alpha':['1',1]}},
           '3':{'class_type':'ImageScale','inputs':{'image':['2',0],'upscale_method':'lanczos','width':268,'height':164,'crop':'disabled'}},
           '4':{'class_type':'SaveImage','inputs':{'images':['3',0],'filename_prefix':'fallout1_bones_game/'+token}}}
    schemas=q.request(BASE,'/object_info')
    workflow=q.make_workflow(graph,schemas);workflow['extra']['notes']='Deterministic full-canvas scale to original67x41 at4x; no new generation or crop.'
    q.save(RUN,'workflow.json',workflow);q.save(RUN,'prompt-api.json',graph)
    q.require_idle(BASE)
    run=q.request(BASE,'/prompt',{'prompt':graph,'client_id':'bones-prepare-'+token,'extra_data':{'extra_pnginfo':{'workflow':workflow}}})
    q.save(RUN,'run.json',run)
for _ in range(120):
    history=q.request(BASE,'/history/'+run['prompt_id'])
    if run['prompt_id'] in history:break
    time.sleep(1)
record=history[run['prompt_id']];q.save(RUN,'history.json',record)
assert record['status']['status_str']=='success',record['status']
data=q.request(BASE,'/view?'+urllib.parse.urlencode(record['outputs']['4']['images'][0]))
(RUN/'v13bones.png').write_bytes(data)
im=Image.open(RUN/'v13bones.png');assert im.mode=='RGBA' and im.size==(268,164)
pixels=im.tobytes();assert min(pixels[3::4])==0 and max(pixels[3::4])==255
payload=struct.pack('<4sIIII',b'F1HD',1,268,164,4)+pixels
PACK.mkdir(parents=True,exist_ok=True)
(PACK/'v13bones.png').write_bytes(data);(PACK/'v13bones.rgba').write_bytes(payload)
manifest={'component':'v13ent-door-skeleton','operation':'ComfyUI Lanczos full-canvas mapping to native67x41 x4; lossless RGBA packaging',
 'source':str(SOURCE),'source_sha256':q.sha_file(SOURCE),'png_sha256':q.sha_bytes(data),'rgba_sha256':q.sha_bytes(payload),
 'native_dimensions':[67,41],'hd_dimensions':[268,164],'scale':4,'fid':113,'pid':211,'frame':0,
 'tile':17488,'elevation':0,'direction_offset':[20,30],'frame_shift':[0,0],
 'anchor_native':[13,10],'alpha':'native soft alpha retained; no original-mask clipping',
 'geometry':'original full FRM canvas and object placement retained; no crop or added offsets',
 'aspect_mapping':'1312x800 generated canvas mapped to268x164 (less than0.5percent aspect correction)',
 'comfy_prompt_id':run['prompt_id'],'installed':False}
q.save(PACK,'manifest.json',manifest);q.save(RUN,'manifest.json',manifest)
print(json.dumps(manifest,indent=2))
