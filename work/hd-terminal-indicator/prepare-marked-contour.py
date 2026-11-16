"""Read the user's red guide; construct and apply its matte in ComfyUI nodes."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse,shutil
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('qwen-terminal.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
OUT=ROOT/'assets/generated/v13ent-terminal/user-contour-v4-20261114'
OLD=ROOT/'assets/hd/v13ent/terminal-natural-edge-v2'
GUIDE=Path('C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-98783ae5-0a02-4381-a38b-d5d5a990384c.png')
def save(name,v):(OUT/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def trace():
 # Read-only geometry analysis. Only numeric rectangles are sent to Comfy;
 # Python does not resample, recolor, paint, or write the actual sprite pixels.
 a=np.array(Image.open(GUIDE).convert('RGB')).astype(int)
 red=(a[:,:,0]>90)&(a[:,:,0]>a[:,:,1]+70)&(a[:,:,0]>a[:,:,2]+70)
 closed=ndimage.binary_closing(red,iterations=6)
 filled=ndimage.binary_fill_holes(closed)
 labels,n=ndimage.label(filled);sizes=np.bincount(labels.ravel());sizes[0]=0
 assert sizes.max()>250000
 inside=ndimage.binary_erosion(labels==sizes.argmax(),iterations=3)
 # Exact screenshot registration: sprite rectangle x23 y15, 483x800.
 # At 2x the delivered HD size the final Comfy area filter creates a narrow AA edge.
 xs=(23+(np.arange(256)+0.5)*483/256).astype(int)
 ys=(15+(np.arange(424)+0.5)*800/424).astype(int)
 mask=inside[ys[:,None],xs[None,:]]
 rectangles=[];previous={}
 for y,row in enumerate(mask):
  edges=np.diff(np.pad(row.astype(int),(1,1)))
  spans=list(zip(np.where(edges==1)[0].tolist(),np.where(edges==-1)[0].tolist()))
  active={}
  for left,right in spans:
   key=(left,right)
   if key in previous:
    index=previous[key];rectangles[index][3]+=1
   else:
    index=len(rectangles);rectangles.append([left,y,right-left,1])
   active[key]=index
  previous=active
 return rectangles
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Saved run exists; use collect')
 h.h.require_idle(h.BASE);shutil.copy2(GUIDE,OUT/'user-marked-reference.png')
 rectangles=trace();save('trace-rectangles.json',rectangles)
 uploads={name:h.h.upload(h.BASE,p,'terminal-traced-'+uuid.uuid4().hex+'.png') for name,p in [('original',h.OUT/'source.png'),('off',OLD/'terminal-off.png'),('on',OLD/'terminal-on.png')]}
 graph={}
 def add(kind,**kw):
  k=str(len(graph)+1);graph[k]=h.n(kind,**kw);return [k,0]
 mask=add('SolidMask',value=0.0,width=256,height=424)
 for x,y,w,height in rectangles:
  patch=add('SolidMask',value=1.0,width=w,height=height)
  mask=add('MaskComposite',destination=mask,source=patch,x=x,y=y,operation='add')
 image=add('MaskToImage',mask=mask)
 image=add('ImageScale',image=image,upscale_method='area',width=128,height=212,crop='disabled')
 mask=add('ImageToMask',image=image,channel='red')
 original=add('LoadImage',image=uploads['original'])
 original_opacity=add('InvertMask',mask=[original[0],1])
 mask=add('MaskComposite',destination=mask,source=original_opacity,x=0,y=0,operation='multiply')
 alpha=add('InvertMask',mask=mask)
 outputs={};prefix='fallout1_terminal_user_contour/'+uuid.uuid4().hex
 for state in ['off','on']:
  old=add('LoadImage',image=uploads[state]);rgba=add('JoinImageWithAlpha',image=old,alpha=alpha)
  node=add('SaveImage',images=rgba,filename_prefix=prefix+'/terminal-'+state);outputs[node[0]]='terminal-'+state+'.png'
 image=add('MaskToImage',mask=mask);node=add('SaveImage',images=image,filename_prefix=prefix+'/precise-opacity');outputs[node[0]]='precise-opacity.png'
 wf=h.h.make_workflow(graph,h.h.request(h.BASE,'/object_info'))
 save('prompt-api.json',graph);save('workflow.json',wf);save('outputs.json',outputs)
 save('plan.json',dict(method='User red outline -> closed largest contour -> 2x HD scanline rectangles -> Comfy area AA matte; original FRM support cap. RGB remains approved V2.',registration=dict(x=23,y=15,width=483,height=800),red_threshold=70,close_pixels=6,inward_pixels=3,rectangles=len(rectangles),nodes=len(graph),working=[256,424],target=[128,212],guide_sha256=h.h.sha_file(GUIDE),source=str(OLD),diffusion=False))
 h.h.require_idle(h.BASE);run=h.h.request(h.BASE,'/prompt',dict(prompt=graph,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(dict(run=run,rectangles=len(rectangles),nodes=len(graph))))
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.h.request(h.BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.h.request(h.BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected user contour')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
