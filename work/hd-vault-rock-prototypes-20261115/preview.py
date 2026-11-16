"""Native Comfy sprite assembly for prototype comparison, never runtime writes."""
from pathlib import Path
import sys,uuid,json
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import generate as z
p=z.p;R=z.R;OUT=z.OUT
SELECTED={'a':'a','b':'b-v3','c':'c-v2'}
PREVIEW=OUT/'preview-v2'

def compose():
 d=PREVIEW
 if (d/'run.json').exists():p.execute(d,{},{});return
 # Lossless decoding of existing game assets for a neutral-light assembly.
 assets={a['asset_id']:a for a in p.read(z.w.DATA/'manifest.json')['assets']}
 for id in [16,160,183,119,110]:z.w.decode(z.w.DATA/assets[id]['filename']).save(OUT/'inputs'/('asset-%03d.png'%id))
 g={};outputs={};prefix='fallout1_vault_rock_prototypes/preview-'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 def rgba(path):n=load(path);return add('JoinImageWithAlpha',image=n,alpha=[n[0],1])
 def over(dst,src,x,y):
  split=add('SplitImageWithAlpha',image=src)
  return add('ImageCompositeMasked',destination=dst,source=split,mask=add('InvertMask',mask=[split[0],1]),x=x,y=y,resize_source=False)
 def save(im,file):n=add('SaveImage',images=im,filename_prefix=prefix+'/'+file);outputs[n[0]]=file+'.png'
 canvas=add('EmptyImage',width=1536,height=960,batch_size=1,color=0x181B1B)
 # Original local registration: door object152, frame153, rock252.
 door=rgba(OUT/'inputs/asset-160.png');frame=rgba(OUT/'inputs/asset-016.png')
 scene=over(canvas,door,360,136)
 scene=over(scene,frame,0,0)
 for name in ['original','a','b','c']:
  if name=='original':sprite=rgba(OUT/'inputs/original.png');x,y=1088,236
  else:
   path=OUT/SELECTED[name]/'prototype.png';arr=np.array(Image.open(path).convert('RGBA'));yy,xx=np.where(arr[:,:,3]>180)
   box=[max(0,int(xx.min())-2),max(0,int(yy.min())-2),min(arr.shape[1],int(xx.max())+3),min(arr.shape[0],int(yy.max())+3)]
   loaded=load(path);opaque=add('InvertMask',mask=[loaded[0],1]);opaque=add('ThresholdMask',mask=opaque,value=.70)
   feather=add('ImageBlur',image=add('MaskToImage',mask=opaque),blur_radius=2,sigma=.75);opaque=add('ImageToMask',image=feather,channel='red')
   clean=add('JoinImageWithAlpha',image=loaded,alpha=add('InvertMask',mask=opaque))
   crop=add('ImageCrop',image=clean,x=box[0],y=box[1],width=box[2]-box[0],height=box[3]-box[1]);width=min(316,round((box[2]-box[0])*960/(box[3]-box[1])))
   fitted=add('ImageScale',image=crop,upscale_method='lanczos',width=width,height=960,crop='disabled')
   blank=add('EmptyImage',width=384,height=1024,batch_size=1,color=0);blank=add('JoinImageWithAlpha',image=blank,alpha=add('SolidMask',value=1.,width=384,height=1024))
   selected=add('ImageCompositeMasked',destination=blank,source=fitted,x=316-width,y=32,resize_source=False);save(selected,name+'-selected')
   sprite=add('ImageScale',image=selected,upscale_method='lanczos',width=192,height=512,crop='disabled');x,y=1054,220
  view=over(scene,sprite,x,y)
  view=add('ImageCrop',image=view,x=944,y=172,width=352,height=584);save(view,name+'-context')
 p.execute(d,g,outputs)

def sheets():
 d=OUT/'review';d.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
 names=['original','a','b','c'];labels=['Сейчас','A — узкая кромка','B — слоистые уступы','C — наклонный скол']
 sheet=Image.new('RGB',(1536,1170),(24,27,27));draw=ImageDraw.Draw(sheet)
 for i,(name,label) in enumerate(zip(names,labels)):
  draw.text((i*384+16,16),label,font=font,fill='#dedbd1')
  im=Image.open(OUT/'a/input.png' if name=='original' else PREVIEW/(name+'-selected.png')).convert('RGBA');im.thumbnail((192,512),Image.Resampling.LANCZOS);sheet.paste(im,(i*384+(384-im.width)//2,58),im)
  view=Image.open(PREVIEW/(name+'-context.png')).convert('RGB');sheet.paste(view,(i*384+16,586))
 sheet.save(d/'comparison.png')
 for name,label in zip(names[1:],labels[1:]):
  pair=Image.new('RGB',(704,640),(24,27,27));dr=ImageDraw.Draw(pair);dr.text((16,12),label,font=font,fill='#dedbd1')
  im=Image.open(PREVIEW/(name+'-selected.png')).convert('RGBA');im.thumbnail((224,584),Image.Resampling.LANCZOS);pair.paste(im,((352-im.width)//2,50),im)
  view=Image.open(PREVIEW/(name+'-context.png')).convert('RGB');pair.paste(view,(352,50));pair.save(d/('prototype-'+name+'.png'))
 # Quantify the alpha change in the same registration, without modifying it.
 base=np.array(Image.open(OUT/'a/input.png').convert('RGBA'))[:,:,3]>127;qa=[]
 for name in names[1:]:
  a=np.array(Image.open(PREVIEW/(name+'-selected.png')).convert('RGBA'));mask=a[:,:,3]>127
  qa.append(dict(variant=name,alpha_changed_pixels=int((base!=mask).sum()),original_hanging_region_removed=int((base&~mask)[:540].sum()),opaque_pixels=int(mask.sum()),transparent=bool((a[:,:,3]==0).any()),prompt_id=p.read(OUT/SELECTED[name]/'run.json')['prompt_id']))
 p.save(d/'manifest.json',dict(status='prototypes, not installed',context='manual exact-position sprite assembly with current vault frame and door, neutral light; not a game screenshot',variants=qa,images=[str((d/('prototype-'+n+'.png')).relative_to(R)) for n in names[1:]]))
 for f,h in p.read(OUT/'baseline.json').items():assert p.sha(R/f)==h,f
 print('Saved comparison; runtime executable, registry manifest and AGENTS unchanged',flush=True)

if __name__=='__main__':
 compose();sheets()
