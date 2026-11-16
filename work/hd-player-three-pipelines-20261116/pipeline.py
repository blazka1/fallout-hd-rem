"""Original FRM comparison: Qwen / DreamShaper / SeedVR2 + DreamShaper.

All model inference uses the existing local ComfyUI. No runtime writes.
"""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, sys, time, urllib.request, urllib.parse, uuid
from datetime import datetime, timezone
from PIL import Image
import numpy as np
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'assets/generated/player-male-vault13/three-pipelines-guide-v9-20261116'
REF = ROOT/'assets/reference/player-male-vault13'
MODELS = Path('C:/Users/Administrator/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models')
BASE = 'http://127.0.0.1:8188'
SEED = 161120269
spec=importlib.util.spec_from_file_location('workflow_helpers',ROOT/'work/seedvr2-image-setup/20261113/knife-upscale.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):
    with open(p,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def node(kind,**kw): return dict(class_type=kind,inputs=kw)
def upload(p):
    boundary='player-three-'+uuid.uuid4().hex
    body=b''
    for k,v in dict(type='input',subfolder='fallout1_player_three_pipelines',overwrite='false').items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{p.stem}-{uuid.uuid4().hex}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+p.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(BASE+'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=40) as r: v=json.load(r)
    return v['subfolder']+'/'+v['name']
def execute(name,g,outputs):
    d=OUT/name;d.mkdir(parents=True,exist_ok=True)
    if (d/'result.json').exists(): return
    if not (d/'run.json').exists():
        schema=h.req('/object_info');wf=h.workflow(g,schema)
        wf['last_node_id']=max(map(int,g));wf['extra']['notes']='Four original male Vault 13 poses. HD-TEXTURE-GUIDE comparison; no runtime changes.'
        save(d/'workflow.json',wf);save(d/'prompt-api.json',g);save(d/'outputs.json',outputs)
        while True:
            q=h.req('/queue')
            if not q['queue_running'] and not q['queue_pending']:break
            print('Waiting for existing shared queue; no cancellation.',flush=True);time.sleep(5)
        client='player-three-'+uuid.uuid4().hex
        try:r=h.req('/prompt',dict(prompt=g,client_id=client,extra_data={'extra_pnginfo':{'workflow':wf}}))
        except urllib.error.HTTPError as e:
            (d/'error.json').write_bytes(e.read());raise
        save(d/'run.json',dict(**r,client_id=client,submitted_utc=datetime.now(timezone.utc).isoformat()))
        print('SUBMITTED',name,r['prompt_id'],flush=True)
    pid=read(d/'run.json')['prompt_id'];outputs=read(d/'outputs.json');t=time.monotonic()
    while True:
        job=h.req('/history/'+pid).get(pid)
        if job:break
        if time.monotonic()-t>3600:raise TimeoutError('Resume saved prompt_id; do not resubmit.')
        time.sleep(3)
    save(d/'history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    records=[]
    for nid,filename in outputs.items():
        rec=job['outputs'][nid]['images'][0]
        with urllib.request.urlopen(BASE+'/view?'+urllib.parse.urlencode(rec),timeout=60) as r:data=r.read()
        p=d/filename
        if p.exists() and p.read_bytes()!=data:raise RuntimeError('Different existing result')
        p.write_bytes(data);im=Image.open(p)
        records.append(dict(file=filename,sha256=sha(p),size=im.size,mode=im.mode))
    events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save(d/'result.json',dict(status='experiment, not installed',prompt_id=pid,elapsed_seconds=elapsed,files=records))
    print('DONE',name,elapsed,flush=True)

def prepare():
    if (OUT/'plan.json').exists():return
    inputs=OUT/'inputs';inputs.mkdir(parents=True,exist_ok=True)
    plan=read(ROOT/'assets/generated/player-male-vault13/original-seed-qwen-4poses-20261116/plan.json')
    atlas=Image.new('RGBA',(128,192));records=[]
    for p in plan['poses']:
        source=ROOT/p['source'];assert sha(source)==p['sha256']
        im=Image.open(source).convert('RGBA');atlas.paste(im,(p['x'],p['y']))
        (inputs/(p['name']+'.png')).write_bytes(source.read_bytes())
        frm='hmjmpsaa.frm' if p['action']=='stand' else 'hmjmpsab.frm'
        meta=read(REF/'metadata/art/critters'/(frm+'.json'))
        sheet=next(s for s in meta['sheets'] if s['direction']==p['direction'])
        cell=next(c for c in sheet['cells'] if c['index']==p['frame'])
        records.append(dict(**p,frame_shift=[cell['shift_x'],cell['shift_y']],
            direction_offset=[meta['direction_x'][p['direction']],meta['direction_y'][p['direction']]],
            fps=meta['fps'],action_frame=meta['action_frame'],anchor_policy='FRM logical offsets unchanged; atlas placement recorded separately'))
        for folder in ['raw','metadata']:
            src=REF/folder/'art/critters'/(frm if folder=='raw' else frm+'.json')
            dst=inputs/'source-records'/src.name;dst.parent.mkdir(exist_ok=True);dst.write_bytes(src.read_bytes())
        indexed=REF/'frames/art/critters'/frm/f"d{p['direction']}-f{p['frame']:03}.png"
        (inputs/(p['name']+'-indexed.png')).write_bytes(indexed.read_bytes())
    atlas.save(inputs/'original-atlas.png')
    atlas.resize((512,768),Image.Resampling.NEAREST).save(inputs/'original-nearest-x4.png')
    atlas.resize((512,768),Image.Resampling.LANCZOS).save(inputs/'original-lanczos-x4.png')
    palette=REF/'raw/color.pal'
    if palette.exists():(inputs/'source-records/color.pal').write_bytes(palette.read_bytes())
    tracked=[ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'protected-before.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked if p.is_file()})
    save(OUT/'plan.json',dict(status='experiment',poses=records,native_atlas=[128,192],working_atlas=[512,768],target_scales=[2,4],
        source='Original FRM only; no ImageGen or earlier Qwen artwork used',seed=SEED,
        branches=['original -> Qwen 2.1 Edit','original -> DreamShaper XL v2 Turbo','original -> SeedVR2 -> DreamShaper XL v2 Turbo'],
        sdxl=dict(denoise_trials=[0.15,0.22,0.30],steps=8,cfg=2,sampler='dpmpp_sde',scheduler='karras'),
        qwen=dict(steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1,reference_conditioning=True),
        alpha='Raw model results retained; delivery masks from common original Lanczos x4 control. Mask overlap alone does not validate contents.',
        dimensions='Native atlas padded to 128x192; x4=512x768 divisible by32 and8; no anisotropic resizing',runtime_modified=False))
    print('PREPARED source inventory and protected hashes',flush=True)

def models():
    names=['checkpoints/DreamShaperXL_Turbo_v2.safetensors','diffusion_models/qwen_image_2.1_int8_convrot.safetensors','text_encoders/qwen3vl_8b_int8_convrot.safetensors','vae/qwen_image_2.1_vae_bf16.safetensors','diffusion_models/seedvr2_3b_int8_convrot.safetensors','vae/seedvr2_ema_vae_fp16.safetensors']
    save(OUT/'model-files.json',[dict(file=str(MODELS/n),bytes=(MODELS/n).stat().st_size,sha256=sha(MODELS/n)) for n in names])
    print('Recorded hashes for six model files',flush=True)

COMMON=('Four original Fallout 1 male Vault Dweller sprites in a fixed two by two atlas: '
    'upper left front three-quarter idle, upper right rear three-quarter idle, lower left southeast walking step, lower right west-facing walking step. '
    'Original late-1990s prerendered isometric game art, restrained moderately HD restoration. '
    'Worn muted dark blue fabric jumpsuit, ochre yellow collar and front stripe and waistband, original small yellow 13 on the back, brown boots, bare hands, short brown hair. '
    'Ordinary adult male face, natural simple features, no beauty retouching. Readable broad forms, selective fabric wear, subtle dusty folds. '
    'Keep original silhouettes, proportions, positions, joint angles, direction, foot contact, spacing and original upper-left lighting and ground shadows. '
    'Preserve the original palette, camera and costume design. No armor, weapons, bags, modern tactical outfit, added ornaments or new shadow extensions. ')
def qwen():
    name='qwen-direct'
    if (OUT/name/'run.json').exists():execute(name,{},{});return
    prompt=COMMON+('Restore only the existing four figures; improve material readability with restrained surface detail. '
        'Retain fine raster character without coarse enlarged pixel blocks, cartoon simplification, excessive detail or plastic smoothing. '
        'Exact original two by two sprite layout on transparent empty background. No ground plane, scenery, labels or extra figures.')
    g={'1':node('LoadImage',image=upload(OUT/'inputs/original-lanczos-x4.png')),
       '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
       '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
       '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
       '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
       '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['2',0]}),
       '9':node('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=SEED,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.),
       '10':node('VAEDecode',samples=['9',0],vae=['6',0]),
       '11':node('SaveImage',images=['10',0],filename_prefix='fallout1_player_three/'+uuid.uuid4().hex+'/qwen-direct')}
    save(OUT/name/'text-prompts.json',dict(positive=prompt,negative=''))
    execute(name,g,{'11':'raw.png'})

def seed():
    name='seedvr2-control'
    if (OUT/name/'run.json').exists():execute(name,{},{});return
    g=read(ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113/prompt-api.json')
    g['1']['inputs']['image']=upload(OUT/'inputs/original-atlas.png');g['9']['inputs']['seed']=SEED
    prefix='fallout1_player_three/'+uuid.uuid4().hex
    g['12']['inputs']['filename_prefix']=prefix+'/seedvr2-x4';g['13']['inputs']['filename_prefix']=prefix+'/lanczos-x4'
    execute(name,g,{'12':'raw.png','13':'lanczos-control.png'})

def control():
    name='qwen-original-control'
    g={'1':node('LoadImage',image=upload(OUT/'dream-direct/d15/input-rgb.png')),
       '2':node('Canny',image=['1',0],low_threshold=.12,high_threshold=.32),
       '3':node('SaveImage',images=['2',0],filename_prefix='fallout1_player_three/'+uuid.uuid4().hex+'/original-canny')}
    execute(name,g,{'3':'canny.png'})

def qwen_controlled():
    name='qwen-direct-controlled'
    if (OUT/name/'run.json').exists():execute(name,{},{});return
    g=read(OUT/'qwen-direct/prompt-api.json')
    g['12']=node('LoadImage',image=upload(OUT/'qwen-original-control/canny.png'))
    g['13']=node('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors')
    g['14']=node('ZImageFunControlnet',model=['7',0],model_patch=['13',0],vae=['6',0],strength=.8,image=['12',0],start_percent=0.,end_percent=.85)
    g['9']['inputs']['model']=['14',0]
    g['11']['inputs']['filename_prefix']='fallout1_player_three/'+uuid.uuid4().hex+'/qwen-original-controlled'
    save(OUT/name/'text-prompts.json',read(OUT/'qwen-direct/text-prompts.json'))
    save(OUT/name/'change.json',dict(reason='First Qwen pass altered geometry and lost original shadow coverage',
        changed_only='Add original-image Canny control strength .8, start0 end.85; all sampler/prompt/reference settings identical',
        source='Original FRM; no SeedVR2 input in this branch'))
    execute(name,g,{'11':'raw.png'})

def qwen_soft():
    name='qwen-direct-soft'
    if (OUT/name/'run.json').exists():execute(name,{},{});return
    g=read(OUT/'qwen-direct-controlled/prompt-api.json')
    g['14']['inputs']['strength']=.3
    g['11']['inputs']['filename_prefix']='fallout1_player_three/'+uuid.uuid4().hex+'/qwen-original-soft'
    save(OUT/name/'text-prompts.json',read(OUT/'qwen-direct/text-prompts.json'))
    save(OUT/name/'change.json',dict(reason='Strong .8 control reproduced coarse flat faces and white opaque background; rejected',
        changed_only='Control strength .8 -> .3; same source, prompt, seed, sampler and end_percent'))
    execute(name,g,{'11':'raw.png'})

def dream(branch,denoise):
    name=f'{branch}/d{round(denoise*100):02}'
    if (OUT/name/'run.json').exists():execute(name,{},{});return
    p=OUT/('inputs/original-lanczos-x4.png' if branch=='dream-direct' else 'seedvr2-control/raw.png')
    im=Image.open(p).convert('RGBA');assert im.size==(512,768)
    # SDXL is RGB. A single neutral background for both branches; alpha stays independent.
    bg=Image.new('RGBA',im.size,(62,62,58,255));bg.alpha_composite(im)
    inp=OUT/name/'input-rgb.png';inp.parent.mkdir(parents=True,exist_ok=True);bg.convert('RGB').save(inp)
    positive=COMMON+'Isolated four separate sprites on a plain muted neutral grey background. Detailed rendered 2D RPG sprite shading, restrained cloth texture.'
    negative='photograph, glamour, handsome fashion model, anime, cartoon, flat illustration, thick outlines, plastic, glossy, oversharpening, grain, noise, oversaturated, redesign, armor, weapons, props, extra limbs, extra figures, landscape, scenery, text, watermark, border'
    g={'1':node('CheckpointLoaderSimple',ckpt_name='DreamShaperXL_Turbo_v2.safetensors'),
       '2':node('LoadImage',image=upload(inp)),
       '3':node('CLIPTextEncode',clip=['1',1],text=positive),
       '4':node('CLIPTextEncode',clip=['1',1],text=negative),
       '5':node('VAEEncode',pixels=['2',0],vae=['1',2]),
       '6':node('KSampler',model=['1',0],positive=['3',0],negative=['4',0],latent_image=['5',0],seed=SEED,steps=8,cfg=2.,sampler_name='dpmpp_sde',scheduler='karras',denoise=denoise),
       '7':node('VAEDecode',samples=['6',0],vae=['1',2]),
       '8':node('SaveImage',images=['7',0],filename_prefix='fallout1_player_three/'+uuid.uuid4().hex+'/'+branch+f'-d{denoise:.2f}')}
    save(OUT/name/'text-prompts.json',dict(positive=positive,negative=negative))
    execute(name,g,{'8':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','models','qwen','seed','dream','control','qwen_controlled','qwen_soft']);a=p.parse_args()
    if a.stage=='dream':
        for branch in ['dream-direct','seed-dream']:
            for strength in [.15,.22,.30]:dream(branch,strength)
    else:globals()[a.stage]()
