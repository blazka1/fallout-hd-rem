"""Register generated wall accents into the matched base, preserving joins."""
import sys,uuid
from pathlib import Path
import numpy as np
from PIL import Image
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT

def run(theme):
 d=OUT/('prepared/accents-v3' if theme in ['moss','mushrooms'] else 'prepared/accents-v2')/theme
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 plan=p.read(OUT/'plan.json');layout=p.read(OUT/'qwen/accents'/theme/'layout.json');g={};outputs={};info=[];prefix='fallout1_wall_variety/registered/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 def mul(a,b):return add('MaskComposite',destination=a,source=b,x=0,y=0,operation='multiply')
 def color(a):return int(a[0]*65536+a[1]*256+a[2])
 for a in layout:
  context=next(c for c in plan['contexts'] if any(s['source']=='art/walls/'+a['source']+'.frm' for s in c['selected']))
  basepath=OUT/'prepared/material-v2'/context['id']/'assets'/('asset-%03d.png'%a['base'])
  srcpath=OUT/'qwen/accents'/theme/'crops'/('asset-%03d.png'%a['id'])
  corrected=OUT/'qwen/accents-refined'/('asset-%03d'%a['id'])/'crop.png'
  if corrected.exists():srcpath=corrected
  old=np.array(Image.open(basepath).convert('RGBA'));height,width=old.shape[:2]
  raw=np.array(Image.open(srcpath).convert('RGBA').resize((width,height),Image.Resampling.LANCZOS))
  box=[round(width*.12),round(height*.30),round(width*.88),round(height*.84)]
  if theme=='mushrooms':
   rgb=raw.astype(int);growth=(rgb[:,:,0]-rgb[:,:,2]>6)&(rgb[:,:,1]-rgb[:,:,2]>4)&(rgb[:,:,3]>200)
   growth[:box[1]]=False;growth[box[3]:]=False;growth[:,:box[0]]=False;growth[:,box[2]:]=False
   yy,xx=np.where(growth);assert len(xx)>10,a['id']
   box=[max(6,int(xx.min())-8),max(round(height*.3),int(yy.min())-8),min(width-6,int(xx.max())+9),min(round(height*.84),int(yy.max())+9)]
  x0,y0,x1,y1=box
  neutral=(old[:,:,3]>200)&(old[:,:,0]>25)&(raw[:,:,3]>200)&(raw[:,:,:3].mean(2)>15)&(np.ptp(raw[:,:,:3].astype(int),axis=2)<15)
  neutral[y0:y1,x0:x1]=False
  assert neutral.sum()>50,(theme,a['id'])
  target=old[:,:,:3][neutral].mean(0);actual=raw[:,:,:3][neutral].mean(0);ratio=target/np.maximum(actual,1)
  gain=np.rint(np.clip(ratio,.4,1)*255).astype(int);lift=np.rint(np.clip((target-actual)/(255-actual),0,.3)*255).astype(int)
  base=load(basepath);src=load(srcpath);scaled=add('ImageScale',image=src,upscale_method='lanczos',width=width,height=height,crop='disabled')
  flat=add('EmptyImage',width=width,height=height,batch_size=1,color=color(gain));matched=add('ImageBlend',image1=scaled,image2=flat,blend_factor=1.,blend_mode='multiply')
  flat=add('EmptyImage',width=width,height=height,batch_size=1,color=color(lift));matched=add('ImageBlend',image1=matched,image2=flat,blend_factor=1.,blend_mode='screen')
  opaque=add('InvertMask',mask=[base[0],1]);mask=add('GrowMask',mask=opaque,expand=-6,tapered_corners=False)
  rect=add('SolidMask',value=0.,width=width,height=height);inside=add('SolidMask',value=1.,width=x1-x0,height=y1-y0)
  inside=add('FeatherMask',mask=inside,left=8,top=12,right=8,bottom=12);rect=add('MaskComposite',destination=rect,source=inside,x=x0,y=y0,operation='add');mask=mul(mask,rect)
  if theme!='mushrooms':
   light=add('ImageToMask',image=base,channel='red');light=add('ThresholdMask',mask=light,value=24/255);mask=mul(mask,light)
  # Leave empty pixels created by the model alone, preserving a solid wall.
  generated=add('ImageScale',image=add('MaskToImage',mask=add('InvertMask',mask=[src[0],1])),upscale_method='lanczos',width=width,height=height,crop='disabled')
  generated=add('ImageToMask',image=generated,channel='red');mask=mul(mask,generated)
  red=add('ImageToMask',image=scaled,channel='red');green=add('ImageToMask',image=scaled,channel='green');blue=add('ImageToMask',image=scaled,channel='blue')
  rg=add('MaskComposite',destination=red,source=green,x=0,y=0,operation='subtract');rg=add('ThresholdMask',mask=rg,value=.12)
  bg=add('MaskComposite',destination=blue,source=green,x=0,y=0,operation='subtract');bg=add('ThresholdMask',mask=bg,value=.12)
  mask=mul(mask,add('InvertMask',mask=mul(rg,bg)))
  if theme=='moss':
   rb=add('MaskComposite',destination=red,source=blue,x=0,y=0,operation='subtract');rb=add('ThresholdMask',mask=rb,value=.025)
   gb=add('MaskComposite',destination=green,source=blue,x=0,y=0,operation='subtract');gb=add('ThresholdMask',mask=gb,value=.018)
   growth=mul(rb,gb);growth=add('GrowMask',mask=growth,expand=3,tapered_corners=True)
   growth=add('MaskToImage',mask=growth);growth=add('ImageBlur',image=growth,blur_radius=2,sigma=1.)
   growth=add('ImageToMask',image=growth,channel='red');mask=mul(mask,growth)
   mask=mul(mask,add('SolidMask',value=.55,width=width,height=height))
  composed=add('ImageCompositeMasked',destination=base,source=matched,x=0,y=0,resize_source=False,mask=mask);result=add('JoinImageWithAlpha',image=composed,alpha=[base[0],1])
  save=add('SaveImage',images=result,filename_prefix=prefix+'/asset-%03d'%a['id']);outputs[save[0]]='assets/asset-%03d.png'%a['id']
  save=add('SaveImage',images=add('MaskToImage',mask=mask),filename_prefix=prefix+'/mask-%03d'%a['id']);outputs[save[0]]='masks/asset-%03d.png'%a['id']
  info.append(dict(**a,source_png=str(srcpath.relative_to(R)),base_png=str(basepath.relative_to(R)),edit_box_hd=box,gain=(gain/255).tolist(),screen_lift=(lift/255).tolist(),color_sample='neutral stone outside accent window; mushroom/moss colors excluded',alpha='exact base alpha',protected_dark_roof=True))
 p.save(d/'registration.json',info);p.execute(d,g,outputs)
if __name__=='__main__':
 for theme in ['cavities','cracks','moss','mushrooms']:
  if len(sys.argv)==1 or sys.argv[1]==theme:run(theme)
