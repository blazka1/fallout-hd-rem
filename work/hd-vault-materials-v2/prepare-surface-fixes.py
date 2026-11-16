"""Composite two reviewed Qwen donors only in the approved user selections."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse,shutil
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE;ROOT=z.ROOT
TRIM=ROOT/'assets/generated/v13ent-vault/smooth-trim-v4-20261114'
RECESS=ROOT/'assets/generated/v13ent-vault/recess-detail-v6-20261114'
OUT=ROOT/'assets/generated/v13ent-vault/surface-fixes-v4-20261114/prepared'
SOURCE=ROOT/'assets/hd/v13ent/vault-clean-trim-v3/asset-016.png'
def submit():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'run.json').exists();h.require_idle(BASE)
 g={};outputs={};prefix='fallout1_vault_surface_fixes/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(BASE,p,'surface-fixes-'+uuid.uuid4().hex+'.png'))
 old=load(SOURCE);trim=load(TRIM/'raw.png');trim=add('ImageScale',image=trim,upscale_method='lanczos',width=1368,height=896,crop='disabled')
 mask=add('ImageToMask',image=load(TRIM/'edit-mask.png'),channel='red')
 cover=add('ThresholdMask',mask=add('ImageToMask',image=trim,channel='red'),value=0.035)
 trim_mask=add('MaskComposite',destination=mask,source=cover,x=0,y=0,operation='multiply')
 ch=[add('MaskToImage',mask=add('ImageToMask',image=trim,channel=c)) for c in ['red','green','blue']]
 gray=add('ImageBlend',image1=ch[0],image2=ch[1],blend_factor=0.7708558,blend_mode='normal');gray=add('ImageBlend',image1=gray,image2=ch[2],blend_factor=0.0722,blend_mode='normal')
 trim=add('ImageBlend',image1=trim,image2=gray,blend_factor=0.94,blend_mode='normal')
 black=add('EmptyImage',width=1368,height=896,batch_size=1,color=0)
 trim=add('ImageBlend',image1=trim,image2=black,blend_factor=0.04,blend_mode='normal')
 result=add('ImageCompositeMasked',destination=old,source=trim,x=0,y=0,resize_source=False,mask=trim_mask)
 recess=load(RECESS/'raw.png');recess=add('ImageScale',image=recess,upscale_method='lanczos',width=192,height=224,crop='disabled')
 local_mask_image=load(RECESS/'edit-mask-local.png');local_mask=add('ImageToMask',image=local_mask_image,channel='red')
 # A two-pixel interior transition avoids a rectangular material boundary.
 soft=add('ImageBlur',image=local_mask_image,blur_radius=2,sigma=1.0);soft=add('ImageToMask',image=soft,channel='red')
 soft=add('MaskComposite',destination=local_mask,source=soft,x=0,y=0,operation='multiply')
 result=add('ImageCompositeMasked',destination=result,source=recess,x=224,y=576,resize_source=False,mask=soft)
 result=add('JoinImageWithAlpha',image=result,alpha=[old[0],1])
 union=add('MaskComposite',destination=mask,source=local_mask,x=224,y=576,operation='add')
 for im,name in [(result,'asset-016'),(add('MaskToImage',mask=union),'edit-mask')]:
  k=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for n,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs),('provenance.json',dict(source=str(SOURCE),trim_prompt=json.loads((TRIM/'run.json').read_text())['prompt_id'],recess_prompt=json.loads((RECESS/'run.json').read_text())['prompt_id'],trim_brightness_factor=0.96,recess_crop=[224,576,192,224]))]:z.save(OUT,n,v)
 h.require_idle(BASE);z.save(OUT,'run.json',h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})))
 print('Submitted registered material composite')
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running',pid);return
 job=hist[pid];z.save(OUT,'history.json',job);assert job['status']['status_str']=='success',job['status']
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected surface fixes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);globals()[p.parse_args().action]()
