"""ComfyUI-only shadow adjustment; Python archives, validates and packs results."""
from pathlib import Path
import importlib.util,json,uuid,time,urllib.parse,struct,argparse
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'assets/generated/v13ent-door-skeleton-qwen/shadow-strength-v3-20261113'
PACK=ROOT/'assets/hd/v13ent-door-skeleton/v3-shadow-x4'
parser=argparse.ArgumentParser();profiles=parser.add_mutually_exclusive_group();profiles.add_argument('--classic-contrast',action='store_true');profiles.add_argument('--balanced',action='store_true');args=parser.parse_args()
params={'alpha_threshold':.75,'grow_hd_px':2,'blur_radius_hd_px':8,'sigma':2.8,'offset_y_hd_px':4,'max_underlay_alpha':.36,'canvas_edge_feather_hd_px':8}
if args.classic_contrast:
    RUN=ROOT/'assets/generated/v13ent-door-skeleton-qwen/shadow-classic-v4-20261113'
    PACK=ROOT/'assets/hd/v13ent-door-skeleton/v4-classic-shadow-x4'
    params.update(grow_hd_px=3,blur_radius_hd_px=4,sigma=1.1,offset_y_hd_px=6,max_underlay_alpha=.84,canvas_edge_feather_hd_px=4)
if args.balanced:
    RUN=ROOT/'assets/generated/v13ent-door-skeleton-qwen/shadow-balanced-v5-20261113'
    PACK=ROOT/'assets/hd/v13ent-door-skeleton/v5-balanced-shadow-x4'
    params.update(grow_hd_px=3,blur_radius_hd_px=6,sigma=1.95,offset_y_hd_px=5,max_underlay_alpha=.60,canvas_edge_feather_hd_px=6)
SOURCE=ROOT/'assets/hd/v13ent-door-skeleton/v2-shadow-x4/v13bones.png'
spec=importlib.util.spec_from_file_location('trial',ROOT/'assets/generated/v13ent-door-skeleton-qwen/trial-v1-20261113/run-qwen21-edit.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
BASE='http://127.0.0.1:8188';RUN.mkdir(parents=True,exist_ok=True)
if (PACK/'manifest.json').exists():raise SystemExit('Package already exists; preserve it')
if (RUN/'run.json').exists():
    run=json.loads((RUN/'run.json').read_text())
else:
    q.require_idle(BASE);token=uuid.uuid4().hex
    uploaded=q.upload(BASE,SOURCE,'shadow-strength-'+token+'.png')
    g={}
    def node(i,kind,**inputs):g[str(i)]={'class_type':kind,'inputs':inputs}
    node(1,'LoadImage',image=uploaded)
    node(2,'InvertMask',mask=['1',1])
    node(3,'ThresholdMask',mask=['2',0],value=.75)
    node(4,'GrowMask',mask=['3',0],expand=params['grow_hd_px'],tapered_corners=True)
    node(5,'MaskToImage',mask=['4',0])
    node(6,'ImageBlur',image=['5',0],blur_radius=params['blur_radius_hd_px'],sigma=params['sigma'])
    node(7,'ImageToMask',image=['6',0],channel='red')
    node(8,'SolidMask',value=0.,width=268,height=164)
    node(9,'MaskComposite',destination=['8',0],source=['7',0],x=0,y=params['offset_y_hd_px'],operation='add')
    node(10,'SolidMask',value=params['max_underlay_alpha'],width=268,height=164)
    edge=params['canvas_edge_feather_hd_px']
    node(11,'FeatherMask',mask=['10',0],left=edge,top=edge,right=edge,bottom=edge)
    node(12,'MaskComposite',destination=['9',0],source=['11',0],x=0,y=0,operation='multiply')
    node(13,'InvertMask',mask=['12',0])
    node(14,'EmptyImage',width=268,height=164,batch_size=1,color=0)
    node(15,'PorterDuffImageComposite',source=['1',0],source_alpha=['1',1],destination=['14',0],destination_alpha=['13',0],mode='SRC_OVER')
    node(16,'JoinImageWithAlpha',image=['15',0],alpha=['15',1])
    node(17,'SaveImage',images=['16',0],filename_prefix='fallout1_bones_shadow/'+token)
    workflow=q.make_workflow(g,q.request(BASE,'/object_info'))
    q.save(RUN,'workflow.json',workflow);q.save(RUN,'prompt-api.json',g)
    q.require_idle(BASE)
    run=q.request(BASE,'/prompt',{'prompt':g,'client_id':'bones-shadow-'+token,'extra_data':{'extra_pnginfo':{'workflow':workflow}}})
    q.save(RUN,'run.json',run)
for _ in range(120):
    h=q.request(BASE,'/history/'+run['prompt_id'])
    if run['prompt_id'] in h:break
    time.sleep(1)
record=h[run['prompt_id']];q.save(RUN,'history.json',record)
assert record['status']['status_str']=='success'
data=q.request(BASE,'/view?'+urllib.parse.urlencode(record['outputs']['17']['images'][0]))
(RUN/'v13bones.png').write_bytes(data)
im=Image.open(RUN/'v13bones.png');assert im.mode=='RGBA' and im.size==(268,164)
a=np.asarray(Image.open(SOURCE)).astype(int);b=np.asarray(im).astype(int)
opaque=a[:,:,3]==255
assert np.abs(a[:,:,:3][opaque]-b[:,:,:3][opaque]).max()<=1
assert b[:,:,3].min()==0 and b[:,:,3].max()==255
assert (b[:,:,3]-a[:,:,3]).max()>10
PACK.mkdir(parents=True,exist_ok=True);(PACK/'v13bones.png').write_bytes(data)
payload=struct.pack('<4sIIII',b'F1HD',1,268,164,4)+im.tobytes()
(PACK/'v13bones.rgba').write_bytes(payload)
m=json.loads((SOURCE.parent/'manifest.json').read_text())
m.update(source=str(SOURCE),source_sha256=q.sha_file(SOURCE),png_sha256=q.sha_bytes(data),rgba_sha256=q.sha_bytes(payload),installed=False,
 operation='ComfyUI soft black underlay from body alpha; original sprite composited above unchanged',
 comfy_prompt_id=run['prompt_id'],shadow_parameters=params,
 checks={'opaque_body_rgb_max_error':int(np.abs(a[:,:,:3][opaque]-b[:,:,:3][opaque]).max()),'unchanged_dimensions':True,'new_game_objects':0},
 geometry='Same native67x41 registration and full canvas; no scale or shift of body')
m.pop('integration_receipt',None)
q.save(PACK,'manifest.json',m);q.save(RUN,'manifest.json',m)
print(json.dumps(m,indent=2))
