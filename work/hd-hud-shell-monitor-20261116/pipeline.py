"""Preview-only HUD shell: original -> SeedVR2 -> Qwen 2.1 with Canny control."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, urllib.request, urllib.parse, uuid
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'assets/generated/hud-shell-monitor/seed-qwen-v1-20261116'
SOURCE = ROOT/'assets/reference/hud-panel-audit-20261115/png/iface-00.png'
spec = importlib.util.spec_from_file_location('hud_helpers',ROOT/'work/hd-inventory-brass-knuckles/20261113/seed-knuckles.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
PROMPT = '''Faithfully restore this exact original Fallout 1 1997 bottom HUD panel as a high resolution 2D game UI texture. Keep the entire very wide shallow panel, exact original composition, straight-on view, proportions and all existing positions. Preserve the exact left monitor housing silhouette, rounded rectangular black monitor opening, asymmetric thick beveled steel rim, existing diagonal split and chips across the upper rim, lower lip, corner fasteners, seams and the existing narrow central and right metal dividers. Preserve the original muted olive-gray worn steel and restrained warm brown oxidation, original light direction and brightness, late-1990s Fallout prerendered industrial aesthetic. Refine existing metal with coherent fine grain, small scratches, worn paint and subtle oxidation in existing recesses. Keep every bevel and screw in its current location. The left monitor is powered off: dark charcoal glass, original faint broad irregular gray reflection, no content, no glow, no scanlines. Remove pixel dithering and colored speckle without making the metal smooth plastic or shiny chrome. Restore material detail only. Preserve every button, label, number, light, hatch and central weapon rectangle exactly as reference context, without redrawing their design. Do not invent text, symbols, objects, controls, tubes, cables, rivets or ornaments. Do not change layout, crop, perspective, monitor opening size or corner curvature. No redesign, no modern sci-fi styling, no neon, no added damage, no excessive rust, no text on the monitor. Fully filled opaque canvas. There are only tiny repeated-edge padding strips above and below the panel; keep registration with the reference.'''

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def n(kind,**inputs): return dict(class_type=kind,inputs=inputs)
def upload(path):
    token=uuid.uuid4().hex; boundary='hud-'+token
    body=b''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k,v in dict(type='input',subfolder='fallout1_hud_shell_monitor',overwrite='false').items())
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.stem}-{token}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
    body+=path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(h.BASE+'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=30) as r: data=json.load(r)
    return data['subfolder']+'/'+data['name']

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'source.json').exists(): return
    im=Image.open(SOURCE).convert('RGB'); assert im.size==(640,100)
    im.save(OUT/'original.png')
    Image.fromarray(np.pad(np.asarray(im),((2,2),(0,0),(0,0)),mode='edge')).save(OUT/'source-padded.png')
    save(OUT/'source.json',dict(source=str(SOURCE),sha256=sha(SOURCE),native=[640,100],padding=[0,2,0,2],
        seed_working=[2560,416],qwen_working=[2560,416],final=[3840,600],status='experiment-before-installation',runtime_installed=False))
    save(Path(__file__).with_name('task.json'),dict(component='HUD shell and log monitor',status='preview in preparation',
        output=str(OUT),scope='SeedVR2 then Qwen; protected controls; no runtime integration',shared_files_modified=[]))

def submit(stage):
    prepare(); folder=OUT/stage;folder.mkdir(exist_ok=True)
    if (folder/'run.json').exists(): raise RuntimeError('Existing prompt retained; use collect.')
    h.idle(); schemas=h.req('/object_info'); prefix='fallout1_hud_shell_monitor/'+stage+'-'+uuid.uuid4().hex
    if stage=='seed':
        image=upload(OUT/'source-padded.png')
        g={
          '1':n('LoadImage',image=image),
          '2':n('ImageScaleBy',image=['1',0],upscale_method='lanczos',scale_by=4.0),
          '3':n('UNETLoader',unet_name='seedvr2_3b_int8_convrot.safetensors',weight_dtype='default'),
          '4':n('VAELoader',vae_name='seedvr2_ema_vae_fp16.safetensors'),
          '5':n('SeedVR2Preprocess',resized_images=['2',0]),
          '6':n('VAEEncodeTiled',pixels=['5',0],vae=['4',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '7':n('SeedVR2Conditioning',model=['3',0],vae_conditioning=['6',0]),
          '8':n('KSampler',model=['3',0],positive=['7',0],negative=['7',1],latent_image=['6',0],seed=16112026,steps=1,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
          '9':n('VAEDecodeTiled',samples=['8',0],vae=['4',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '10':n('SeedVR2PostProcessing',images=['9',0],original_resized_images=['2',0],color_correction_method='none'),
          '11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/seed-padded'),
          '12':n('ImageCrop',image=['10',0],width=2560,height=400,x=0,y=8),
          '13':n('SaveImage',images=['12',0],filename_prefix=prefix+'/seed-hud'),
          '14':n('SaveImage',images=['2',0],filename_prefix=prefix+'/lanczos-padded')}
        save(folder/'parameters.json',dict(model='seedvr2_3b_int8_convrot.safetensors',seed=16112026,steps=1,cfg=1,scale=4))
    elif stage=='control':
        image=upload(OUT/'seed/seed-padded.png')
        g={'1':n('LoadImage',image=image),'2':n('Canny',image=['1',0],low_threshold=0.25,high_threshold=0.65),
           '3':n('SaveImage',images=['2',0],filename_prefix=prefix+'/canny')}
    else:
        source=OUT/'seed/seed-padded.png'; image=upload(source); control=upload(OUT/'control/canny.png')
        assert Image.open(source).size==(2560,416)
        g={
          '1':n('LoadImage',image=image),
          '2':n('LoadImage',image=control),
          '3':n('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
          '4':n('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
          '5':n('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
          '6':n('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'),
          '7':n('QwenImage21Cache',model=['3',0],device='cpu',dtype='default'),
          '8':n('ZImageFunControlnet',model=['7',0],model_patch=['6',0],vae=['5',0],strength=1.0,image=['2',0],start_percent=0.0,end_percent=1.0),
          '9':n('TextEncodeQwenImage21',clip=['4',0],prompt=PROMPT,negative_prompt='',vae=['5',0],resolution=0,**{'images.image_1':['1',0]}),
          '10':n('KSampler',model=['8',0],positive=['9',0],negative=['9',1],latent_image=['9',2],seed=16112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
          '11':n('VAEDecodeTiled',samples=['10',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '12':n('SaveImage',images=['11',0],filename_prefix=prefix+'/qwen-padded'),
          '13':n('ImageCrop',image=['11',0],width=2560,height=400,x=0,y=8),
          '14':n('ImageScale',image=['13',0],upscale_method='lanczos',width=3840,height=600,crop='disabled'),
          '15':n('SaveImage',images=['14',0],filename_prefix=prefix+'/qwen-master')}
        save(folder/'parameters.json',dict(models=['qwen_image_2.1_int8_convrot.safetensors','qwen3vl_8b_int8_convrot.safetensors','qwen_image_2.1_vae_bf16.safetensors','qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'],
            input=str(source),input_sha256=sha(source),control=str(OUT/'control/canny.png'),control_strength=1,seed=16112026,steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1))
        (folder/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    wf=h.workflow(g,schemas);wf['extra']['notes']='HUD shell/monitor preview only; SeedVR2 -> Qwen 2.1; no installation.'
    save(folder/'workflow.json',wf);save(folder/'prompt-api.json',g)
    h.idle()
    result=h.req('/prompt',dict(prompt=g,client_id='hud-shell-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}))
    save(folder/'run.json',result); assert not result.get('node_errors'),result
    print(json.dumps(result),flush=True)

def collect(stage):
    folder=OUT/stage;pid=json.loads((folder/'run.json').read_text())['prompt_id']; history=h.req('/history/'+pid)
    if pid not in history:
        q=h.req('/queue');print(json.dumps(dict(status='running',prompt_id=pid,running_count=len(q['queue_running']),pending_count=len(q['queue_pending']))));return
    job=history[pid];save(folder/'history.json',job)
    if job['status']['status_str']!='success': raise RuntimeError(job['status'])
    outputs={'seed':{'11':'seed-padded.png','13':'seed-hud.png','14':'lanczos-padded.png'},
             'control':{'3':'canny.png'},'qwen':{'12':'qwen-padded.png','15':'qwen-master.png'}}[stage]
    files=[]
    for nid,name in outputs.items():
        record=job['outputs'][nid]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=60) as r: (folder/name).write_bytes(r.read())
        im=Image.open(folder/name);files.append(dict(file=name,size=list(im.size),mode=im.mode,sha256=sha(folder/name)))
    events=dict(job['status']['messages'])
    save(folder/'result.json',dict(prompt_id=pid,files=files,elapsed_seconds=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000,runtime_installed=False))
    print(json.dumps(files),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','submit','collect']);parser.add_argument('stage',nargs='?',choices=['seed','control','qwen']);a=parser.parse_args()
    prepare() if a.action=='prepare' else submit(a.stage) if a.action=='submit' else collect(a.stage)
