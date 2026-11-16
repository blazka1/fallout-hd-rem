"""Exact-layout QA; no artistic processing of textures."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT
F=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
def material():
 plan=p.read(OUT/'plan.json');selected={};qa=OUT/'review';qa.mkdir(exist_ok=True)
 records=[]
 for c in plan['contexts']:
  d=OUT/'prepared/material-v2'/c['id']
  if not (d/'result.json').exists():continue
  for row in p.read(d/'registration.json')['records']:
   path=d/'assets'/('asset-%03d.png'%row['id']);a=np.array(Image.open(path).convert('RGBA'))
   oldpath=OUT/('inputs/walls' if row['kind']=='base' else 'inputs/old-variants')/((row['source'] if row['kind']=='base' else Path(row['file']).stem)+'.png')
   old=np.array(Image.open(oldpath).convert('RGBA'));assert a.shape==old.shape
   assert np.array_equal(a[:,:,3],old[:,:,3]),row
   changed=np.any(a!=old,axis=2);border=np.zeros(changed.shape,bool);border[:4]=1;border[-4:]=1;border[:,:4]=1;border[:,-4:]=1
   assert not changed[border].any(),row
   assert not changed[(old[:,:,3]>0)&(old[:,:,0]<=24)].any(),row
   records.append(dict(id=row['id'],source=row['source'],kind=row['kind'],changed_pixels=int(changed.sum()),alpha_exact=True,border_4px_exact=True,dark_roof_exact=True))
   if row['kind']=='base':selected[row['source']]=path
 for c in plan['contexts']:
  if not (OUT/'prepared/material-v2'/c['id']/'result.json').exists():continue
  sheet=Image.new('RGB',(2400,856),(24,27,27));draw=ImageDraw.Draw(sheet)
  for i,variant in enumerate(['current','matched']):
   im=Image.new('RGB',(2400,1600));x0,y0,*_=c['box_native']
   for s in c['placements']:
    stem=Path(s['source']).stem;path=selected.get(stem) if variant=='matched' else None
    if path is None:path=OUT/'inputs/walls'/(stem+'.png')
    sprite=Image.open(path).convert('RGBA');im.paste(sprite,((s['x']-x0)*4,(s['y']-y0)*4),sprite)
   sheet.paste(im.resize((1200,800),Image.Resampling.LANCZOS),(i*1200,56))
   draw.text((i*1200+14,14),c['id']+(' / текущие стены' if i==0 else ' / согласованный материал')+' — без игрового света',font=F,fill='#ddd7c7')
  sheet.save(qa/(c['id']+'-material-neighbors.png'))
 p.save(qa/'material-checks.json',records)
 print('Validated',len(records),'wall images, alpha / border / dark roof unchanged',flush=True)
if __name__=='__main__':material()
