"""Restore only the user-marked soft patch below the terminal cable."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse,shutil
import numpy as np
from PIL import Image
from scipy import ndimage
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE;ROOT=z.ROOT;OUT=ROOT/'assets/generated/v13ent-vault/recess-detail-v6-20261114'
SOURCE=ROOT/'assets/hd/v13ent/vault-clean-trim-v3/asset-016.png'
GUIDE=Path('C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-ac628e54-fd7e-42fc-a9e0-49cb77a69a7d.png')
PROMPT='''Restore sharp coherent surface detail in this exact isometric Fallout vault frame crop. Keep the curved cable, all straight plate edges, the vertical narrow metal post on the right, the diagonal lower sill, the original lighting and exact perspective fixed. The large rusted FRONT PANEL at the left has a smooth blurry dark patch near its LOWER RIGHT corner, immediately BELOW THE CURVED CABLE and to the LEFT of the vertical post. Repair that blurry patch by extending the same crisp irregular pitted iron and orange-brown corrosion already visible on the adjacent large panel. Continue that same richly detailed material naturally across the ENTIRE front panel to its right edge and lower diagonal edge: sharp tiny irregular rust crevices, chipped surface, fine scratches and consistent microcontrast. The patch should look like part of the same continuous metal sheet, with no smudged triangular area, stretched diagonal texture, or plastic-smooth blank stain. Do not brighten the shadow or add an artificial outline. Do not change shapes or move the cable, do not add a terminal, bolts, seams or objects. Preserve empty areas and the narrow side post. Crisp late-1990s prerendered Fallout metal, matching neighboring material rather than random sharpening noise.'''
def submit():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'run.json').exists();h.require_idle(BASE)
 a=np.array(Image.open(GUIDE).convert('RGB')).astype(int);red=(a[:,:,0]>140)&(a[:,:,0]>a[:,:,1]+100)&(a[:,:,0]>a[:,:,2]+100)
 filled=ndimage.binary_fill_holes(ndimage.binary_closing(red,iterations=4));lab,n=ndimage.label(filled);sizes=np.bincount(lab.ravel());sizes[0]=0
 inside=ndimage.binary_erosion(lab==sizes.argmax(),iterations=2)
 # Exact source/screenshot registration verified on an unmarked region: zero RGB error.
 # Screenshot x=source_master_x+12, y=source_master_y-3; master is 2x crop(0,320,512,576).
 xx=12+(224+np.arange(192))*2+1;yy=(576+np.arange(224)-320)*2-3+1
 selected=inside[yy[:,None],xx[None,:]];rects=[];prev={}
 for y,row in enumerate(selected):
  edges=np.diff(np.pad(row.astype(int),(1,1)));active={}
  for l,r in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
   key=(int(l),int(r))
   if key in prev:i=prev[key];rects[i][3]+=1
   else:i=len(rects);rects.append([int(l),y,int(r-l),1])
   active[key]=i
  prev=active
 g={};outputs={};prefix='fallout1_recess_detail/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 src=add('LoadImage',image=h.upload(BASE,SOURCE,'recess-detail-'+uuid.uuid4().hex+'.png'))
 crop=add('ImageCrop',image=src,x=224,y=576,width=192,height=224)
 ref=add('ImageScale',image=crop,upscale_method='lanczos',width=768,height=896,crop='disabled')
 mask=add('SolidMask',value=0.0,width=192,height=224)
 for x,y,w,ht in rects:
  p=add('SolidMask',value=1.0,width=w,height=ht);mask=add('MaskComposite',destination=mask,source=p,x=x,y=y,operation='add')
 models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
 schemas,checks=h.preflight(BASE,models);assert checks['ready_to_submit']
 model=add('UNETLoader',unet_name=models['unet'],weight_dtype='default');clip=add('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default');vae=add('VAELoader',vae_name=models['vae'])
 cache=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=PROMPT,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':ref})
 sam=add('KSampler',model=cache,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=1411202661,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
 im=add('VAEDecode',samples=sam,vae=vae)
 for image,name in [(ref,'reference'),(im,'raw'),(add('MaskToImage',mask=mask),'edit-mask-local')]:
  k=add('SaveImage',images=image,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 wf=h.make_workflow(g,schemas)
 for name,value in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs),('preflight.json',checks),('selection.json',dict(crop=[224,576,192,224],guide_offset=[12,-3],guide_scale=2,source_job='306f07b6-6dad-48a0-a00a-bdb0345bda75',rectangles=rects))]:z.save(OUT,name,value)
 shutil.copy2(GUIDE,OUT/'user-guide.png');(OUT/'prompt.txt').write_text(PROMPT,encoding='utf-8')
 h.require_idle(BASE);z.save(OUT,'run.json',h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})))
 print('Submitted local Qwen recess detail')
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running',pid);return
 job=hist[pid];z.save(OUT,'history.json',job);assert job['status']['status_str']=='success'
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected recess detail')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);globals()[p.parse_args().action]()
