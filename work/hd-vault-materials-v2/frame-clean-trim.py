"""Local Comfy color correction, restricted to the user's red-marked back faces."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse,shutil
import numpy as np
from PIL import Image
from scipy import ndimage
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE;ROOT=z.ROOT
OUT=ROOT/'assets/generated/v13ent-vault/clean-trim-v3-20261114'
SRC=ROOT/'assets/hd/v13ent/vault-materials-v2/asset-016.png'
GUIDE=Path('C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-c88eead8-a15b-462e-9236-690f021b88a0.png')
def save(n,v):z.save(OUT,n,v)
def geometry():
 # Read-only annotation analysis. RGB/alpha pixels are modified only in Comfy.
 a=np.array(Image.open(GUIDE).convert('RGB')).astype(int)
 red=(a[:,:,0]>130)&(a[:,:,0]>a[:,:,1]+90)&(a[:,:,0]>a[:,:,2]+90)
 filled=ndimage.binary_fill_holes(ndimage.binary_closing(red,iterations=4))
 labels,n=ndimage.label(filled);sizes=np.bincount(labels.ravel());sizes[0]=0
 top=labels==sizes.argmax();assert 28000<top.sum()<31000
 # The left-hand annotation is open along its outside edge. Close that face
 # explicitly on the sprite silhouette, following the marked inner boundary.
 poly=[(16,286),(79,329),(82,345),(69,345),(69,368),(79,383),(78,474),(69,590),(65,611),(76,628),(66,635),(65,654),(76,667),(77,700),(66,715),(16,665)]
 yy,xx=np.mgrid[:a.shape[0],:a.shape[1]];inside=np.zeros(xx.shape,bool)
 for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]):
  if y1!=y2:inside^=((y1>yy)!=(y2>yy))&(xx<(x2-x1)*(yy-y1)/(y2-y1)+x1)
 selected=(top|inside)[27:923,16:1384]
 assert selected.shape==(896,1368)
 rects=[];prev={}
 for y,row in enumerate(selected):
  edges=np.diff(np.pad(row.astype(int),(1,1)));active={}
  for l,r in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
   key=(int(l),int(r))
   if key in prev:i=prev[key];rects[i][3]+=1
   else:i=len(rects);rects.append([int(l),y,int(r-l),1])
   active[key]=i
  prev=active
 return rects,poly
def submit():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'run.json').exists()
 h.require_idle(BASE);rects,poly=geometry();save('selection.json',dict(registration=[16,27,1368,896],rectangles=rects,left_polygon=poly))
 shutil.copy2(GUIDE,OUT/'user-guide.png');g={};outputs={};prefix='fallout1_clean_trim/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 src=add('LoadImage',image=h.upload(BASE,SRC,'frame-trim-'+uuid.uuid4().hex+'.png'))
 mask=add('SolidMask',value=0.0,width=1368,height=896)
 for x,y,w,ht in rects:
  p=add('SolidMask',value=1.0,width=w,height=ht);mask=add('MaskComposite',destination=mask,source=p,x=x,y=y,operation='add')
 alpha=add('InvertMask',mask=[src[0],1]);mask=add('MaskComposite',destination=mask,source=alpha,x=0,y=0,operation='multiply')
 ch=[add('MaskToImage',mask=add('ImageToMask',image=src,channel=c)) for c in ['red','green','blue']]
 gray=add('ImageBlend',image1=ch[0],image2=ch[1],blend_factor=0.7708558,blend_mode='normal')
 gray=add('ImageBlend',image1=gray,image2=ch[2],blend_factor=0.0722,blend_mode='normal')
 clean=add('ImageBlend',image1=src,image2=gray,blend_factor=0.96,blend_mode='normal')
 white=add('EmptyImage',width=1368,height=896,batch_size=1,color=16777215)
 clean=add('ImageBlend',image1=clean,image2=white,blend_factor=0.075,blend_mode='normal')
 result=add('ImageCompositeMasked',destination=src,source=clean,x=0,y=0,resize_source=False,mask=mask)
 result=add('JoinImageWithAlpha',image=result,alpha=[src[0],1])
 for im,name in [(result,'asset-016'),(add('MaskToImage',mask=mask),'edit-mask')]:
  out=add('SaveImage',images=im,filename_prefix=prefix+'/'+name);outputs[out[0]]=name+'.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for n,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs)]:save(n,v)
 h.require_idle(BASE);save('run.json',h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})))
 print('Submitted local masked color correction')
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save('history.json',job);assert job['status']['status_str']=='success',job['status']
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected clean metal trim')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);globals()[p.parse_args().action]()
