"""Local Qwen repair of the old terminal recess, followed by masked Comfy prep."""
from pathlib import Path
import importlib.util,json,uuid,argparse,urllib.parse
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('q',Path(__file__).with_name('qwen-terminal.py'))
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
h=q.h; BASE=q.BASE
OUT=ROOT/'assets/generated/v13ent-terminal/recess-v4-20261114'
FRAME=ROOT/'assets/hd/v13ent/v14-campfire-x4/art/scenery/v13secr3.frm.png'
DOOR=ROOT/'assets/hd/v13ent/v14-campfire-x4/art/scenery/v13secr2.frm/frames/d0-f000.png'
PROMPT='''Repair the small empty dark terminal-shaped cutout in the LOWER LEFT part of this exact Fallout vault entrance image. It is the narrow vertical black slot below the thin curved cable, directly above the rusty bottom metal sill. Remove this old rectangular cutout completely. Continue the neighboring rusty dark gunmetal vertical door-frame surface naturally across the entire slot, and continue the sloping metal sill cleanly across its bottom. Make it a continuous solid metal frame with consistent aged steel texture and subdued lighting, with no black outline, no green checkerboard, no aura, and no terminal-shaped dark stain. Preserve the thin curved cable above the slot. Preserve the round vault door and its teeth on the right, the metal floor, perspective, framing and geometry everywhere else exactly. There is no terminal in this image: do not add a terminal, screen, controls, new object, sign, glow or extra outline. Only repair the small missing section of metal frame in the lower left, matching adjacent surfaces seamlessly.'''
def save(name,v):(OUT/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('Existing job: collect')
    h.require_idle(BASE)
    models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
    schemas,checks=h.preflight(BASE,models);assert checks['ready_to_submit']
    uploads={k:h.upload(BASE,p,'terminal-recess-'+uuid.uuid4().hex+'.png') for k,p in [('frame',FRAME),('door',DOOR)]}
    g={}
    def add(kind,**kw):
        k=str(len(g)+1);g[k]=q.n(kind,**kw);return [k,0]
    frame=add('LoadImage',image=uploads['frame']);door=add('LoadImage',image=uploads['door'])
    canvas=add('EmptyImage',width=1368,height=896,batch_size=1,color=0)
    dm=add('InvertMask',mask=[door[0],1]);fm=add('InvertMask',mask=[frame[0],1])
    canvas=add('ImageCompositeMasked',destination=canvas,source=door,x=360,y=136,resize_source=False,mask=dm)
    canvas=add('ImageCompositeMasked',destination=canvas,source=frame,x=0,y=0,resize_source=False,mask=fm)
    crop=add('ImageCrop',image=canvas,width=352,height=448,x=192,y=448)
    working=add('ImageScale',image=crop,upscale_method='lanczos',width=448,height=576,crop='disabled')
    outputs={};prefix='fallout1_terminal_recess/'+uuid.uuid4().hex
    for im,name in [(crop,'reference-crop'),(working,'reference-working')]:
        k=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
    unet=add('UNETLoader',unet_name=models['unet'],weight_dtype='default')
    clip=add('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default')
    vae=add('VAELoader',vae_name=models['vae']);cache=add('QwenImage21Cache',model=unet,device='cpu',dtype='default')
    enc=add('TextEncodeQwenImage21',clip=clip,prompt=PROMPT,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':working})
    sample=add('KSampler',model=cache,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=1411202604,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
    decoded=add('VAEDecode',samples=sample,vae=vae);k=add('SaveImage',images=decoded,filename_prefix=prefix+'/recess-raw');outputs[k[0]]='recess-raw.png'
    wf=h.make_workflow(g,schemas);save('workflow.json',wf);save('prompt-api.json',g);save('outputs.json',outputs);save('preflight.json',checks)
    (OUT/'prompt.txt').write_text(PROMPT,encoding='utf-8')
    save('plan.json',dict(frame=str(FRAME),frame_sha256=h.sha_file(FRAME),door=str(DOOR),door_sha256=h.sha_file(DOOR),crop=[192,448,352,448],models=models,seed=1411202604,steps=25,status='candidate_not_installed'))
    h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(run))
def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id'];history=h.request(BASE,'/history/'+pid)
    if pid not in history:print('Running '+pid);return
    job=history[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in json.loads((OUT/'outputs.json').read_text()).items():
        rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
    print('Collected Qwen recess')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
