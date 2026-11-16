"""Restore terminal details locally; freeze lamp/socket and user-traced edge."""
from pathlib import Path
import importlib.util,json,uuid,time,urllib.parse,argparse
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('q',Path(__file__).with_name('qwen-terminal.py'));q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
h=q.h;BASE=q.BASE;OUT=ROOT/'assets/generated/v13ent-terminal/detail-v5-20261114';OLD=ROOT/'assets/hd/v13ent/terminal-user-contour-v3'
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Collect existing job')
 h.require_idle(BASE);g={};outputs={};prefix='fallout1_terminal_detail/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=q.n(c,**kw);return [k,0]
 states={state:add('LoadImage',image=h.upload(BASE,OLD/('terminal-'+state+'.png'),'terminal-detail-'+uuid.uuid4().hex+'.png')) for state in ['off','on']}
 src=states['off'];up=add('ImageScale',image=src,upscale_method='lanczos',width=512,height=848,crop='disabled')
 model=add('UNETLoader',unet_name='seedvr2_3b_int8_convrot.safetensors',weight_dtype='default');vae=add('VAELoader',vae_name='seedvr2_ema_vae_fp16.safetensors')
 pre=add('SeedVR2Preprocess',resized_images=up);enc=add('VAEEncodeTiled',pixels=pre,vae=vae,tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8)
 cond=add('SeedVR2Conditioning',model=model,vae_conditioning=enc)
 sampled=add('KSampler',model=model,positive=cond,negative=[cond[0],1],latent_image=enc,seed=1411202620,steps=1,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
 decoded=add('VAEDecodeTiled',samples=sampled,vae=vae,tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8)
 restored=add('SeedVR2PostProcessing',images=decoded,original_resized_images=up,color_correction_method='none')
 donor=add('ImageScale',image=restored,upscale_method='lanczos',width=128,height=212,crop='disabled')
 opaque=add('InvertMask',mask=[src[0],1]);solid=add('ThresholdMask',mask=opaque,value=0.999);inner=add('GrowMask',mask=solid,expand=-2,tapered_corners=False)
 protect=add('SolidMask',value=1.0,width=32,height=35);protect=add('FeatherMask',mask=protect,left=4,top=4,right=4,bottom=4)
 canvas=add('SolidMask',value=0.0,width=128,height=212);canvas=add('MaskComposite',destination=canvas,source=protect,x=88,y=49,operation='add');permit=add('InvertMask',mask=canvas)
 mask=add('MaskComposite',destination=inner,source=permit,x=0,y=0,operation='multiply')
 for state,old in states.items():
  rgb=add('ImageCompositeMasked',destination=old,source=donor,x=0,y=0,resize_source=False,mask=mask)
  rgba=add('JoinImageWithAlpha',image=rgb,alpha=[old[0],1]);k=add('SaveImage',images=rgba,filename_prefix=prefix+'/terminal-'+state);outputs[k[0]]='terminal-'+state+'.png'
 for im,name in [(restored,'restored-master'),(add('MaskToImage',mask=mask),'edit-mask')]:
  k=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 save('workflow.json',wf);save('prompt-api.json',g);save('outputs.json',outputs);save('plan.json',dict(method='Local SeedVR2 restoration, common RGB donor for both lamp states, original alpha and two-HD-pixel edge frozen',source=str(OLD),working=[512,848],target=[128,212],lamp_protection=[92,53,112,76],seed=1411202620,steps=1))
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(run))
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected terminal detail')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
