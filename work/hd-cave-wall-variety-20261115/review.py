"""Comparison sheets from actual assets/captures; no artistic asset changes."""
import sys,html,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT;B=R/'build/hd-cave-wall-variety-20261115';D=B/'review'
F=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
NAMES={'cavities':'Полости','cracks':'Трещины','moss':'Мох','mushrooms':'Грибы'}

def assets():
 D.mkdir(parents=True,exist_ok=True);records=[]
 for theme,label in NAMES.items():
  d=OUT/('prepared/accents-v3' if theme in ['moss','mushrooms'] else 'prepared/accents-v2')/theme
  if not (d/'result.json').exists():continue
  rows=p.read(d/'registration.json');sheet=Image.new('RGB',(1920,650),(22,24,24));draw=ImageDraw.Draw(sheet)
  draw.text((16,12),label+' — слева согласованная основа, справа вариант. Края и прозрачность сохранены.',font=F,fill='#e2ddce')
  for i,a in enumerate(rows):
   before=Image.open(R/a['base_png']).convert('RGBA');after=Image.open(d/'assets'/('asset-%03d.png'%a['id'])).convert('RGBA');old=np.array(before);new=np.array(after)
   assert np.array_equal(old[:,:,3],new[:,:,3]);diff=np.any(old!=new,2);assert diff.sum()>10
   edge=np.zeros(diff.shape,bool);edge[:4]=1;edge[-4:]=1;edge[:,:4]=1;edge[:,-4:]=1;assert not diff[edge].any()
   roof=(old[:,:,3]>0)&(old[:,:,0]<=24)
   if theme=='mushrooms':roof[round(before.height*.3):]=False
   assert not diff[roof].any()
   purple=(new[:,:,0].astype(int)-new[:,:,1]>30)&(new[:,:,2].astype(int)-new[:,:,1]>30)&(new[:,:,3]>0)
   assert not purple.any(),a['id']
   records.append(dict(id=a['id'],theme=theme,changed_pixels=int(diff.sum()),alpha_exact=True,border_exact=True,dark_roof_exact=True,no_magenta=True))
   draw.text((i*320+10,48),str(a['id'])+' / '+a['source'],font=F,fill='#b6b2a9')
   for j,im in enumerate([before,after]):
    im.thumbnail((144,540),Image.Resampling.LANCZOS);sheet.paste(im,(i*320+j*158+(144-im.width)//2+8,88),im)
  sheet.save(D/(theme+'-assets.png'))
 p.save(D/'accent-checks.json',records);print('Reviewed',len(records),'accent assets',flush=True)

def captures():
 world=B/'world-final';rows=p.read(OUT/'plan.json')['new_variants']
 for theme,label in NAMES.items():
  # Tight crop around differences in the real SDL before/after captures.
  selected=[a for a in rows if a['theme']==theme];sheet=Image.new('RGB',(1920,800),(22,24,24));draw=ImageDraw.Draw(sheet)
  draw.text((16,12),label+' — настоящие кадры игры; слева без вариантов стен, справа с вариантами.',font=F,fill='#e2ddce')
  for i,a in enumerate(selected):
   after=Image.open(world/('wall-accent-%d-hd.png'%a['id'])).convert('RGB');before=Image.open(world/('wall-accent-%d-base.png'%a['id'])).convert('RGB')
   # All cameras center on the corresponding wall object; show local context.
   cx,cy=after.width//2,after.height//2
   box=(cx-130,cy-330,cx+130,cy-50)
   for j,im in enumerate([before,after]):
    crop=im.crop(box);crop.thumbnail((300,330),Image.Resampling.LANCZOS);x=(i%3)*640+j*310+10;y=(i//3)*380+60
    sheet.paste(crop,(x,y+30));draw.text((x,y),str(a['id'])+(' / база' if j==0 else ' / вариант'),font=F,fill='#b6b2a9')
  sheet.save(D/(theme+'-game.png'))
 for stem in ['entrance-hd']:
  pairs=[B/'baseline'/(stem+'.png'),world/(stem+'.png')]
  if all(x.exists() for x in pairs):
   sheet=Image.new('RGB',(1920,600),(22,24,24));draw=ImageDraw.Draw(sheet)
   for i,path in enumerate(pairs):
    im=Image.open(path).convert('RGB');im.thumbnail((960,550),Image.Resampling.LANCZOS);sheet.paste(im,(960*i,50));draw.text((960*i+16,12),'До обновления стен' if i==0 else 'Новые стены в игре',font=F,fill='#ddd')
   sheet.save(D/'entrance-before-after.png')

def gallery():
 D.mkdir(parents=True,exist_ok=True)
 images=[]
 for label,name in [('Вход: до и после','entrance-before-after.png')]+[(v+' / ассеты',k+'-assets.png') for k,v in NAMES.items()]+[(v+' / в игре',k+'-game.png') for k,v in NAMES.items()]:
  if (D/name).exists():images.append(f'<h2>{label}</h2><a href="{name}"><img src="{name}"></a>')
 for n in range(1,6):
  name=f'wall-{n:02}-material-neighbors.png';shutil.copy2(OUT/'review'/name,D/name);images.append(f'<h2>Стыки, участок {n}</h2><a href="{name}"><img src="{name}"></a>')
 content='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Стены пещеры — сравнение</title><style>body{background:#161a19;color:#ddd8ca;font:18px system-ui;margin:30px auto;max-width:1500px;padding:0 20px}img{width:100%;height:auto;border:1px solid #444}h2{margin-top:42px}a{color:#b9c5ad}</style><h1>Стены первой пещеры</h1><p>Согласованы 62 исходных фрагмента и 24 прежних варианта. Добавлены 24 новых варианта: по 6 с полостями, трещинами, мхом и грибами. На исходной карте им соответствуют 41 место из 418 стеновых размещений: 10 / 10 / 10 / 11.</p><p>Грибы основаны на трёх уже использованных видах. Полости — детали поверхности; новые проходы и игровые объекты не добавлены. Цвет, края, прозрачность и стыки согласованы с существующей пещерой.</p>'''+''.join(images)+'</html>'
 (D/'index.html').write_text(content,encoding='utf-8')

if __name__=='__main__':
 assets()
 if len(sys.argv)>1 and sys.argv[1]=='game':captures()
 gallery()
