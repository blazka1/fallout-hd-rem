"""Verify localized repairs and build exact renderer comparisons."""
from pathlib import Path
import json,sys,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import prepare as q
R=q.R;p=q.p;O=q.OUT;B=R/'build/hd-cave-seams-20261115';D=B/'review';PACK=R/'assets/hd/v13ent/cave-seams-v1'
def run():
 records=[]
 for a in p.read(PACK/'manifest.json')['records']:
  old=np.array(Image.open(O/'inputs'/('asset-%03d.png'%a['id'])).convert('RGBA'));new=np.array(Image.open(PACK/a['png']).convert('RGBA'));diff=np.any(new!=old,2)
  assert np.array_equal(new[:,:,3],old[:,:,3]);assert diff.any()
  if a['id']>=160 and a['id']<=174:
   allowed=np.zeros(diff.shape,bool);allowed[:40,630:674]=True;assert not diff[~allowed].any(),a['id']
  else:assert not diff[184:].any(),a['id']
  records.append(dict(id=a['id'],changed_pixels=int(diff.sum()),alpha_exact=True,outside_target_unchanged=True))
 before=[np.array(Image.open(O/'inputs'/('asset-%03d.png'%id)).convert('RGBA'))[:40,630:674] for id in range(160,175)]
 after=[np.array(Image.open(PACK/('asset-%03d.png'%id)).convert('RGBA'))[:40,630:674] for id in range(160,175)]
 common=np.all(np.stack(before)==before[0],axis=(0,3));assert common.sum()>1000
 assert all(np.array_equal(a[common],after[0][common]) for a in after)
 p.save(B/'asset-checks.json',dict(records=records,door_static_pixels_all_15_frames=int(common.sum()),door_static_identical=True))
 folder='world' if (B/'world/entrance-hd.png').exists() else 'final-review'
 D.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
 for name,box in [('door',(1000,35,1140,355)),('wall',(1200,100,1640,600)),('entrance',(0,0,1920,1080))]:
  width,height=box[2]-box[0],box[3]-box[1];scale=2 if name=='door' else (.5 if name=='entrance' else 1)
  ww,hh=round(width*scale),round(height*scale);sheet=Image.new('RGB',(ww*2,hh+40),(25,27,26));draw=ImageDraw.Draw(sheet)
  for i,f in enumerate(['diagnostic',folder]):
   im=Image.open(B/f/'entrance-hd.png').crop(box).resize((ww,hh),Image.Resampling.NEAREST if scale>=1 else Image.Resampling.LANCZOS);sheet.paste(im,(i*ww,40));draw.text((i*ww+8,8),'До' if i==0 else 'После',font=font,fill='white')
  sheet.save(D/(name+'-comparison.png'))
 page='<!doctype html><html lang="ru"><meta charset="utf-8"><title>Исправление двух стыков</title><style>body{background:#181b1a;color:#ddd;font:18px system-ui;max-width:1400px;margin:30px auto;padding:20px}img{max-width:100%;height:auto}h2{margin-top:40px}</style><h1>Стыки у входа в Убежище 13</h1><p>Слева — установленная версия до замечаний, справа — исправление. Кадры сняты настоящим рендерером игры при одинаковой камере и освещении.</p><h2>Верхний угол двери</h2><p>Убрана чёрная рваная кромка на отмеченном углу. Исправление одинаково во всех 15 кадрах; остальная дверь сохранена.</p><img src="door-comparison.png"><h2>Верхний переход стены</h2><p>Пять исходных фрагментов и восемь их вариантов сведены по общему изображению участка. Изменён только верхний участок; мох, грибы и детали ниже сохранены.</p><img src="wall-comparison.png"><h2>Полный вход</h2><img src="entrance-comparison.png"></html>'
 (D/'index.html').write_text(page,encoding='utf-8');print('Validated 28 localized edits, exact alpha, unchanged pixels outside targets and consistent 15-frame cap')
if __name__=='__main__':run()
