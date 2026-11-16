"""Complete the open annotation at the left upper cap, in native Comfy nodes."""
from pathlib import Path
import importlib.util,json,uuid,time,urllib.parse
import numpy as np
s=importlib.util.spec_from_file_location('trim',Path(__file__).with_name('frame-clean-trim.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;OUT=z.OUT/'complete';OUT.mkdir(exist_ok=True)
if not (OUT/'run.json').exists():
 h.require_idle(z.BASE);g={};prefix='fallout1_trim_cap/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.z.q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(z.BASE,p,'trim-cap-'+uuid.uuid4().hex+'.png'))
 src=load(z.SRC);existing=load(z.OUT/'edit-mask.png');mask=add('ImageToMask',image=existing,channel='red')
 # Sprite-space polygon: left rear triangle and cap, excludes rusty front face.
 poly=[(7,200),(97,268),(132,283),(72,302),(0,262)]
 yy,xx=np.mgrid[:320,:150];inside=np.zeros(xx.shape,bool)
 for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]):
  if y1!=y2:inside^=((y1>yy)!=(y2>yy))&(xx<(x2-x1)*(yy-y1)/(y2-y1)+x1)
 patch=add('SolidMask',value=0.0,width=150,height=320)
 for y,row in enumerate(inside):
  xs=np.where(row)[0]
  if len(xs):
   p=add('SolidMask',value=1.0,width=int(xs[-1]-xs[0]+1),height=1);patch=add('MaskComposite',destination=patch,source=p,x=int(xs[0]),y=y,operation='add')
 mask=add('MaskComposite',destination=mask,source=patch,x=0,y=0,operation='add')
 mask=add('MaskComposite',destination=mask,source=add('InvertMask',mask=[src[0],1]),x=0,y=0,operation='multiply')
 ch=[add('MaskToImage',mask=add('ImageToMask',image=src,channel=c)) for c in ['red','green','blue']]
 gray=add('ImageBlend',image1=ch[0],image2=ch[1],blend_factor=0.7708558,blend_mode='normal');gray=add('ImageBlend',image1=gray,image2=ch[2],blend_factor=0.0722,blend_mode='normal')
 clean=add('ImageBlend',image1=src,image2=gray,blend_factor=0.96,blend_mode='normal');white=add('EmptyImage',width=1368,height=896,batch_size=1,color=16777215)
 clean=add('ImageBlend',image1=clean,image2=white,blend_factor=0.075,blend_mode='normal')
 result=add('ImageCompositeMasked',destination=src,source=clean,x=0,y=0,resize_source=False,mask=mask);result=add('JoinImageWithAlpha',image=result,alpha=[src[0],1]);outputs={}
 for im,name in [(result,'asset-016'),(add('MaskToImage',mask=mask),'edit-mask')]:
  out=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[out[0]]=name+'.png'
 wf=h.make_workflow(g,h.request(z.BASE,'/object_info'))
 for n,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs),('selection.json',{'left_cap_polygon':poly})]:z.z.save(OUT,n,v)
 h.require_idle(z.BASE);z.z.save(OUT,'run.json',h.request(z.BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})))
pid=json.loads((OUT/'run.json').read_text())['prompt_id']
for _ in range(10):
 hist=h.request(z.BASE,'/history/'+pid)
 if pid in hist:break
 time.sleep(3)
if pid not in hist:print('Still running',pid)
else:
 job=hist[pid];z.z.save(OUT,'history.json',job);assert job['status']['status_str']=='success'
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(z.BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Completed left cap correction')
