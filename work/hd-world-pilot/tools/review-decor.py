"""Review artifacts only: compare actual SDL captures and unchanged production inputs."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'build/hd-world-pilot/preview/floor-decor-v11'
QA=OUT/'qa';QA.mkdir(exist_ok=True)
old=ROOT/'assets/hd/v13ent/v10-neutral-cave-x4'
new=ROOT/'assets/hd/v13ent/v11-floor-decor-x4'
m=json.loads((old/'manifest.json').read_text())
unchanged=[]
for item in m['assets']+m['variants']:
    for field in ('png','metadata'):
        assert (old/item[field]).read_bytes()==(new/item[field]).read_bytes(),item[field]
    unchanged.append(item['asset_id'])
def pixels(path): return np.array(Image.open(path).convert('RGB'))
before=ROOT/'build/hd-world-pilot/preview/neutral-cave-v10'
assert np.array_equal(pixels(before/'entrance-hd.png'), pixels(OUT/'decor-disabled-hd.png'))
assert np.array_equal(pixels(before/'entrance-classic.png'), pixels(OUT/'entrance-classic.png'))
im=Image.open(OUT/'entrance-hd.png').convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
cards=[('Кости',(1070,590,1310,730)),('Бытовой мусор',(820,440,1060,580)),
       ('Пещерные грибы',(1360,580,1600,720)),('Низкие сталагмиты',(1220,520,1460,660))]
sheet=Image.new('RGB',(1000,680),(24,24,24));draw=ImageDraw.Draw(sheet)
for i,(name,box) in enumerate(cards):
    x=(i%2)*500+10;y=(i//2)*340+10
    draw.text((x,y),name,font=font,fill=(220,220,210))
    sheet.paste(im.crop(box).resize((480,280),Image.Resampling.NEAREST),(x,y+40))
sheet.save(QA/'four-decor-in-engine.png')
overview=im.crop((800,400,1620,740))
draw=ImageDraw.Draw(overview)
for label,x,y in [('Кости',1184,656),('Мусор',928,512),('Грибы',1472,660),('Шипы',1344,595)]:
    x-=800;y-=400
    draw.rectangle((x-58,y-28,x+58,y+28),outline=(183,154,91),width=1)
    draw.text((x-58,y+31),label,font=small,fill=(230,207,158),stroke_width=2,stroke_fill=(0,0,0))
overview.save(QA/'placement-overview.png')
poses=Image.new('RGB',(1000,660),(24,24,24));draw=ImageDraw.Draw(poses)
for i,(asset,name,box) in enumerate([(242,'Грибы',(1350,520,1600,720)),(243,'Сталагмиты',(1220,470,1470,670))]):
    for j,direction in enumerate(('front','behind')):
        source=Image.open(OUT/f'decor-{asset}-actor-{direction}.png').convert('RGB')
        x=j*500;y=i*330
        poses.paste(source.crop(box).resize((375,300),Image.Resampling.NEAREST),(x+10,y+30))
        draw.text((x+10,y),name+(' — спереди' if j==0 else ' — сзади'),font=font,fill=(220,220,210))
poses.save(QA/'actor-occlusion.png')
report={'unchanged_existing_images_and_metadata':len(unchanged),'previous_v10_hd_pixel_exact_when_decor_disabled':True,
    'previous_v10_classic_pixel_exact':True,'qa_only_images':['four-decor-in-engine.png','placement-overview.png','actor-occlusion.png'],
    'qa_note':'Crops/resizes/labels only; actual SDL engine captures; no retouching or brightness correction.'}
(QA/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
