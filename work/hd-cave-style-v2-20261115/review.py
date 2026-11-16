"""Side-by-side actual engine frames and literal asset/color audit."""
import json,hashlib,re
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from qa import GROUPS,main as asset_review
R=Path(__file__).resolve().parents[2]
G=R/'assets/generated/v13ent-cave-variety/style-match-v2-20261115'
B=R/'build/hd-cave-style-v2-20261115';OUT=B/'review';OUT.mkdir(parents=True,exist_ok=True)
F=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
asset_review();checks=[]
for gi,(group,sources) in enumerate(GROUPS):
 for i,stem in enumerate(sources):
  name='geo-formation-%02d'%(i+1) if gi==3 else 'geo-rock-%02d'%(gi*4+i+1)
  raw=np.array(Image.open(G/'qwen'/group/'sprites'/(name+'.png')).convert('RGBA'))
  selected=np.array(Image.open(G/'selected'/(name+'.png')).convert('RGBA'))
  ref=np.array(Image.open(R/'assets/generated/v13ent-cave-variety/seedvr2-qwen21-20261115/sources/art/scenery'/(stem+'.frm.current.png')).convert('RGBA'))
  mean=selected[:,:,:3][selected[:,:,3]>200].mean(0);target=ref[:,:,:3][ref[:,:,3]>200].mean(0)
  delta=int(np.abs(raw[:,:,3].astype(int)-selected[:,:,3].astype(int)).max())
  assert delta<=1 and max(abs(mean-target))<1.6,(name,delta,mean,target)
  checks.append(dict(id=name,reference=stem,reference_mean_rgb=target.tolist(),selected_mean_rgb=mean.tolist(),max_mean_channel_error=float(max(abs(mean-target))),max_alpha_quantization=delta,source_sha256=hashlib.sha256((G/'selected'/(name+'.png')).read_bytes()).hexdigest()))
(OUT/'asset-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')

world=B/'world';prior=R/'build/hd-cave-distribution-20261115/enabled-v3'
pairs=[('style-v1-v2',prior/'new-form-224-hd.png',world/'new-form-224-hd.png','Прежние новые формы','Исправленные формы и фактура'),
 ('original-hd-v2',world/'new-form-224-previous-hd.png',world/'new-form-224-hd.png','Исходная HD-пещера','Разнообразие в её стиле')]
evidence=[]
for name,a,b,left,right in pairs:
 box=(420,260,1260,860);sheet=Image.new('RGB',(1680,644),'#191c1c');d=ImageDraw.Draw(sheet)
 for col,(p,title) in enumerate([(a,left),(b,right)]):
  im=Image.open(p).convert('RGB');assert im.size==(1920,1080)
  sheet.paste(im.crop(box),(col*840,44));d.text((col*840+14,10),title,font=F,fill='#e5decd')
 sheet.save(OUT/(name+'.png'))
 evidence.append(dict(file=name+'.png',crop=box,processing='same crop; no color, brightness or scale changes',sources=[dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [a,b]]))
(OUT/'capture-provenance.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
def rel(path):return Path(__import__('os').path.relpath(path,OUT)).as_posix()
page='''<!doctype html><meta charset="utf-8"><title>Пещера — согласование стиля V2</title><style>body{background:#191c1c;color:#e5decd;font:18px Arial;margin:28px}img{max-width:100%;height:auto}section{margin-bottom:40px}a{color:#a9c5c2}</style><h1>Цвет, фактура и форма: исправление V2</h1><p>16 обновлённых спрайтов, прежние 76 назначений и 40 сохранённых оригинальных обликов. Новая генерация Qwen 2.1 опирается на текущие HD-оригиналы и готовые SeedVR2-референсы. RGB согласован нативными узлами ComfyUI; геометрия возвращена к обычным обломкам и наростам.</p><p>Сравнения в игре — реальные SDL-кадры, без ретуши или коррекции освещения.</p>'''
for name,*_ in pairs:page+=f'<section><img src="{name}.png"></section>'
page+='<h2>Исходники и новые варианты</h2><p>Слева направо: оригинал Fallout, прежняя HD-основа, отклонённая новая форма, исправленная версия. В этих таблицах объекты нормированы по размеру только для сравнения; игровые размеры проверены отдельно.</p>'
for group,_ in GROUPS:page+=f'<section><img src="{rel(G/"review"/(group+"-comparison.png"))}"></section>'
page+='<h2>Полные игровые кадры</h2>'
for asset in [224,228,232,236,237,238]:page+=f'<section><h3>Форма {asset}</h3><img src="../world/new-form-{asset}-hd.png"></section>'
(OUT/'index.html').write_text(page,encoding='utf-8')
links=re.findall(r'src="([^"]+)"',page);assert all((OUT/x).exists() for x in links)
print('Review ready;',len(checks),'assets; max mean RGB error',max(x['max_mean_channel_error'] for x in checks))
