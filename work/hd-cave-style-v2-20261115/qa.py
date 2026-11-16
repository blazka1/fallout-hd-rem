"""Literal comparison and numerical analysis; no artwork alteration."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2]
OUT=R/'assets/generated/v13ent-cave-variety/style-match-v2-20261115'
OLD=R/'assets/generated/v13ent-cave-variety/seedvr2-qwen21-20261115'
F=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
SF=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
GROUPS=[('rocks-01',['rock01','rock02','rock03','rock04']),('rocks-02',['rock05','rock06','rock01','rock03']),('rocks-03',['rock04','rock05','rock06','rock02']),('formations',['cstalag1','cstalag2','cvcolum1','cvcolum2'])]
def fit(im,size=300):
 im=im.copy();box=im.getchannel('A').point(lambda x:255 if x>8 else 0).getbbox()
 if box:im=im.crop(box)
 scale=min(size/im.width,size/im.height)
 im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST if scale>2 else Image.Resampling.LANCZOS)
 result=Image.new('RGBA',(size,size),(25,28,28,255));result.alpha_composite(im,((size-im.width)//2,size-im.height));return result.convert('RGB')
def stats(im):
 a=np.array(im.convert('RGBA'));m=a[:,:,3]>200;v=a[:,:,:3][m];lum=v.mean(1)
 return dict(mean_rgb=v.mean(0).tolist(),luma_p10_p50_p90=np.percentile(lum,[10,50,90]).tolist(),opaque_pixels=int(m.sum()),alpha_values=len(np.unique(a[:,:,3])),border_pixels=int(m[0].sum()+m[-1].sum()+m[:,0].sum()+m[:,-1].sum()))
def main():
 review=OUT/'review';review.mkdir(parents=True,exist_ok=True);records=[]
 for gi,(group,sources) in enumerate(GROUPS):
  d=OUT/'qwen'/group
  if not (d/'result.json').exists():continue
  panel=Image.new('RGB',(1280,4*356+65),(25,28,28));draw=ImageDraw.Draw(panel)
  for c,title in enumerate(['Оригинал Fallout','Текущая HD-основа','Прошлая новая форма','Исправленный вариант']):draw.text((c*320+8,16),title,font=SF,fill='#e3dccd')
  for i,stem in enumerate(sources):
   name=('geo-formation-%02d'%(i+1)) if gi==3 else ('geo-rock-%02d'%(gi*4+i+1))
   corrected=OUT/'selected'/(name+'.png')
   if not corrected.exists():corrected=d/'sprites'/(name+'.png')
   paths=[OLD/'sources/art/scenery'/(stem+'.frm.png'),OLD/'sources/art/scenery'/(stem+'.frm.current.png'),OLD/'candidate-pack/new-geometry'/(name+'.png'),corrected]
   ims=[Image.open(p).convert('RGBA') for p in paths]
   for c,im in enumerate(ims):panel.paste(fit(im),(c*320+10,65+i*356));draw.text((c*320+10,65+i*356+307),stem if c<2 else name,font=SF,fill='#ddd5c7')
   records.append(dict(id=name,file=str(corrected.relative_to(R)),sha256=hashlib.sha256(corrected.read_bytes()).hexdigest(),reference=stats(ims[1]),previous=stats(ims[2]),candidate=stats(ims[3])))
  panel.save(review/(group+'-comparison.png'))
 (review/'metrics.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 print(json.dumps([dict(id=x['id'],reference=np.round(x['reference']['luma_p10_p50_p90'],1).tolist(),new=np.round(x['candidate']['luma_p10_p50_p90'],1).tolist(),border=x['candidate']['border_pixels']) for x in records]))
if __name__=='__main__':main()
