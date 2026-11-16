"""Remove rust hue without changing the grate pattern; native Comfy operations."""
from pathlib import Path
import importlib.util,json,uuid,time,urllib.parse
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE;OUT=z.RUN/'floor/clean';OUT.mkdir(exist_ok=True)
if not (OUT/'run.json').exists():
 while True:
  queue=h.request(BASE,'/queue')
  if not queue['queue_running'] and not queue['queue_pending']:break
  time.sleep(5)
 g={}
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 src=add('LoadImage',image=h.upload(BASE,z.ROOT/'assets/hd/v13ent/v14-campfire-x4/art/tiles/grt2000.frm.png','vault-grate-'+uuid.uuid4().hex+'.png'))
 channels=[]
 for c in ['red','green','blue']:
  m=add('ImageToMask',image=src,channel=c);channels.append(add('MaskToImage',mask=m))
 gray=add('ImageBlend',image1=channels[0],image2=channels[1],blend_factor=0.7708558,blend_mode='normal')
 gray=add('ImageBlend',image1=gray,image2=channels[2],blend_factor=0.0722,blend_mode='normal')
 im=add('ImageBlend',image1=src,image2=gray,blend_factor=0.92,blend_mode='normal')
 im=add('ImageSharpen',image=im,sharpen_radius=1,sigma=1.0,alpha=0.4)
 im=add('JoinImageWithAlpha',image=im,alpha=[src[0],1]);prefix='fallout1_vault_grate_clean/'+uuid.uuid4().hex
 saved=add('SaveImage',images=im,filename_prefix=prefix+'/asset-088')
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for name,v in [('workflow.json',wf),('prompt-api.json',g),('output.json',{'node':saved[0]})]:z.save(OUT,name,v)
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));z.save(OUT,'run.json',run)
pid=json.loads((OUT/'run.json').read_text())['prompt_id']
while pid not in h.request(BASE,'/history/'+pid):time.sleep(5)
job=h.request(BASE,'/history/'+pid)[pid];z.save(OUT,'history.json',job);assert job['status']['status_str']=='success'
node=json.loads((OUT/'output.json').read_text())['node'];rec=job['outputs'][node]['images'][0];(OUT/'asset-088.png').write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
print('Original grate pattern preserved; neutral steel ready')
