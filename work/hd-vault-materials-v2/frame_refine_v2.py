"""Preserve repaired recess/cable; SeedVR2 restores its details without redesign."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,time
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE;OUT=z.RUN/'frame/refined-v2';OUT.mkdir(exist_ok=True)
while not (z.RUN/'floor/prepared/asset-088.png').exists():time.sleep(10)
if not (OUT/'run.json').exists():
 while True:
  queue=h.request(BASE,'/queue')
  if not queue['queue_running'] and not queue['queue_pending']:break
  time.sleep(10)
 g={};prefix='fallout1_vault_frame_refined/'+uuid.uuid4().hex;outputs={}
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(BASE,p,'vault-refined-'+uuid.uuid4().hex+'.png'))
 old=load(z.ROOT/'assets/hd/v13ent/terminal-recess-v4/vault-frame.png')
 crop=add('ImageCrop',image=old,x=0,y=320,width=512,height=576)
 enlarged=add('ImageScale',image=crop,upscale_method='lanczos',width=1024,height=1152,crop='disabled')
 model=add('UNETLoader',unet_name='seedvr2_3b_int8_convrot.safetensors',weight_dtype='default');vae=add('VAELoader',vae_name='seedvr2_ema_vae_fp16.safetensors')
 pre=add('SeedVR2Preprocess',resized_images=enlarged)
 enc=add('VAEEncodeTiled',pixels=pre,vae=vae,tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8)
 cond=add('SeedVR2Conditioning',model=model,vae_conditioning=enc)
 sampled=add('KSampler',model=model,positive=cond,negative=[cond[0],1],latent_image=enc,seed=1411202615,steps=1,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
 decoded=add('VAEDecodeTiled',samples=sampled,vae=vae,tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8)
 restore=add('SeedVR2PostProcessing',images=decoded,original_resized_images=enlarged,color_correction_method='none')
 small=add('ImageScale',image=restore,upscale_method='lanczos',width=512,height=576,crop='disabled')
 local=add('SolidMask',value=1.0,width=512,height=576);local=add('FeatherMask',mask=local,left=0,top=24,right=24,bottom=0)
 fallback=add('ImageCompositeMasked',destination=old,source=small,x=0,y=320,resize_source=False,mask=local)
 donor=load(z.RUN/'frame/raw.png');donor=add('ImageScale',image=donor,upscale_method='lanczos',width=1368,height=896,crop='disabled')
 coverage=add('ImageToMask',image=donor,channel='red');coverage=add('ThresholdMask',mask=coverage,value=0.035);coverage=add('GrowMask',mask=coverage,expand=-6,tapered_corners=False)
 opacity=add('InvertMask',mask=[old[0],1]);inner=add('GrowMask',mask=opacity,expand=-4,tapered_corners=False)
 mask=add('MaskComposite',destination=inner,source=coverage,x=0,y=0,operation='multiply')
 protect=add('SolidMask',value=1.0,width=512,height=576);protect=add('FeatherMask',mask=protect,left=0,top=24,right=24,bottom=0)
 full=add('SolidMask',value=0.0,width=1368,height=896);full=add('MaskComposite',destination=full,source=protect,x=0,y=320,operation='add');permit=add('InvertMask',mask=full)
 mask=add('MaskComposite',destination=mask,source=permit,x=0,y=0,operation='multiply')
 final=add('ImageCompositeMasked',destination=fallback,source=donor,x=0,y=0,resize_source=False,mask=mask)
 final=add('JoinImageWithAlpha',image=final,alpha=[old[0],1])
 for im,name in [(final,'asset-016'),(restore,'recess-seedvr2-x2')]:
  k=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for name,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs)]:z.save(OUT,name,v)
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));z.save(OUT,'run.json',run);print('SUBMITTED FRAME REFINEMENT',run['prompt_id'],flush=True)
pid=json.loads((OUT/'run.json').read_text())['prompt_id']
while pid not in h.request(BASE,'/history/'+pid):time.sleep(10)
job=h.request(BASE,'/history/'+pid)[pid];z.save(OUT,'history.json',job)
if job['status']['status_str']!='success':raise RuntimeError(job['status'])
for node,name in json.loads((OUT/'outputs.json').read_text()).items():
 rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
print('REFINED FRAME READY, NOT INSTALLED',flush=True)

