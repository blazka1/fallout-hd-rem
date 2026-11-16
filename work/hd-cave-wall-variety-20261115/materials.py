"""Native Comfy registration/blending of coherent wall donor contexts."""
import sys,uuid
from pathlib import Path
import numpy as np
from PIL import Image
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT

def prepare(name):
 plan=p.read(OUT/'plan.json');c=next(x for x in plan['contexts'] if x['id']==name)
 d=OUT/'prepared/material-v2'/name;src=OUT/'qwen/material'/name/'raw.png'
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 if not src.exists():raise RuntimeError('Material not generated: '+name)
 donor=np.array(Image.open(src).convert('RGB').resize((2400,1600),Image.Resampling.LANCZOS))
 before_sum=np.zeros(3);after_sum=np.zeros(3);count=0
 for s in c['selected']:
  a=plan['walls'][s['source']];old=np.array(Image.open(OUT/'inputs/walls'/(Path(s['source']).stem+'.png')).convert('RGBA'))
  x,y=(s['x']-c['box_native'][0])*4,(s['y']-c['box_native'][1])*4;hh,ww=old.shape[:2]
  own=np.array(Image.open(R/s['ownership_mask']).convert('L').resize((ww,hh),Image.Resampling.NEAREST))>127
  mask=own&(old[:,:,3]>200)&(old[:,:,0]>25);crop=donor[y:y+hh,x:x+ww];mask&=crop.mean(2)>10
  before_sum+=old[:,:,:3][mask].sum(0);after_sum+=crop[mask].sum(0);count+=int(mask.sum())
 ratio=before_sum/np.maximum(after_sum,1);assert ratio.min()>.4 and ratio.max()<1.6,(name,ratio)
 gain=np.rint(np.minimum(ratio,1)*255).astype(int)
 target=before_sum/count;actual=after_sum/count;lift=np.rint(np.clip((target-actual)/(255-actual),0,1)*255).astype(int)
 color=lambda a:int(a[0]*65536+a[1]*256+a[2])
 g={};outputs={};prefix='fallout1_wall_variety/material/'+uuid.uuid4().hex
 def add(kind,**kw):key=str(len(g)+1);g[key]=p.node(kind,**kw);return [key,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 def multiply(a,b):return add('MaskComposite',destination=a,source=b,x=0,y=0,operation='multiply')
 raw=load(src);scaled=add('ImageScale',image=raw,upscale_method='lanczos',width=2400,height=1600,crop='disabled')
 solid=add('EmptyImage',width=2400,height=1600,batch_size=1,color=color(gain))
 matched=add('ImageBlend',image1=scaled,image2=solid,blend_factor=1.,blend_mode='multiply')
 solid=add('EmptyImage',width=2400,height=1600,batch_size=1,color=color(lift))
 matched=add('ImageBlend',image1=matched,image2=solid,blend_factor=1.,blend_mode='screen')
 records=[]
 for s in c['selected']:
  stem=Path(s['source']).stem;a=plan['walls'][s['source']];width,height=s['width']*4,s['height']*4
  old=load(OUT/'inputs/walls'/(stem+'.png'));opaque=add('InvertMask',mask=[old[0],1])
  mask=add('GrowMask',mask=opaque,expand=-6,tapered_corners=False)
  own=load(R/s['ownership_mask']);own=add('ImageScale',image=own,upscale_method='nearest-exact',width=width,height=height,crop='disabled');own=add('ImageToMask',image=own,channel='red')
  mask=multiply(mask,add('GrowMask',mask=own,expand=-4,tapered_corners=False))
  rect=add('SolidMask',value=0.,width=width,height=height);inner=add('SolidMask',value=1.,width=width-8,height=height-8)
  rect=add('MaskComposite',destination=rect,source=inner,x=4,y=4,operation='add');mask=multiply(mask,rect)
  # Preserve the near-black original roof cuts and deep voids exactly.
  visible=add('ImageToMask',image=old,channel='red');visible=add('ThresholdMask',mask=visible,value=24/255)
  mask=multiply(mask,visible)
  blurred=add('MaskToImage',mask=mask);blurred=add('ImageBlur',image=blurred,blur_radius=4,sigma=1.2);soft=add('ImageToMask',image=blurred,channel='red')
  mask=multiply(mask,soft);strength=add('SolidMask',value=.68,width=width,height=height);mask=multiply(mask,strength)
  crop=add('ImageCrop',image=matched,x=(s['x']-c['box_native'][0])*4,y=(s['y']-c['box_native'][1])*4,width=width,height=height)
  targets=[dict(id=a['asset_id'],file=a['filename'],node=old,kind='base',source=stem)]
  for v in plan['old_variants']:
   if v['base']==a['asset_id']:targets.append(dict(id=v['id'],file=v['file'],node=load(OUT/'inputs/old-variants'/(Path(v['file']).stem+'.png')),kind='existing-variant',source=stem))
  for t in targets:
   target_mask=mask
   if t['kind']=='existing-variant':
    target_visible=add('ImageToMask',image=t['node'],channel='red');target_visible=add('ThresholdMask',mask=target_visible,value=24/255)
    target_mask=multiply(mask,target_visible)
   composed=add('ImageCompositeMasked',destination=t['node'],source=crop,x=0,y=0,resize_source=False,mask=target_mask)
   rgba=add('JoinImageWithAlpha',image=composed,alpha=[old[0],1])
   saved=add('SaveImage',images=rgba,filename_prefix=prefix+'/asset-%03d'%t['id']);outputs[saved[0]]='assets/asset-%03d.png'%t['id']
   records.append({k:v for k,v in t.items() if k!='node'})
  saved=add('SaveImage',images=add('MaskToImage',mask=mask),filename_prefix=prefix+'/mask-'+stem);outputs[saved[0]]='masks/'+stem+'.png'
 p.save(d/'registration.json',dict(context=name,records=records,mean_target=target.tolist(),mean_raw=actual.tolist(),gain=(gain/255).tolist(),screen_lift=(lift/255).tolist(),blend=.68,protected_rectangle_border_hd=4,protected_alpha_boundary_hd=6,alpha='exact existing binary alpha',near_black_roof_protected=True))
 p.execute(d,g,outputs)

if __name__=='__main__':
 for c in p.read(OUT/'plan.json')['contexts']:
  if len(sys.argv)==1 or sys.argv[1]==c['id']:prepare(c['id'])
