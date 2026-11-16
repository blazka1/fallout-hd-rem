"""QA-only contact sheets and before/after comparisons of captured engine pixels."""
from pathlib import Path
import json,csv,hashlib,collections
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'build/hd-world-pilot/preview/varied-decor-v13'
QA=OUT/'qa';QA.mkdir(exist_ok=True)
package=ROOT/'assets/hd/v13ent/v13-varied-decor-x4'
parent=ROOT/'assets/hd/v13ent/v11-floor-decor-x4'
m=json.loads((package/'manifest.json').read_text())
old=json.loads((parent/'manifest.json').read_text())
unchanged=0
for item in old['assets']+old['variants']+[d for d in old['decorations'] if d['asset_id']!=243]:
    for field in ('png','metadata'):assert (parent/item[field]).read_bytes()==(package/item[field]).read_bytes()
    unchanged+=1
counts=collections.Counter(p['asset_id'] for p in m['decoration_placements'])
assert counts=={240:1,241:1,242:5,244:1,245:1,246:5,247:4}
assert not any(d['asset_id']==243 for d in m['decorations'])
for oldfile,newfile in [('decor-disabled-hd.png','decor-disabled-hd.png'),('entrance-classic.png','entrance-classic.png')]:
    a=np.array(Image.open(ROOT/'build/hd-world-pilot/preview/floor-decor-v11'/oldfile))
    b=np.array(Image.open(OUT/newfile));assert np.array_equal(a,b),(oldfile,newfile)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
tiles={240:19491,244:24070,245:25729,242:20087,246:20692,247:18689}
labels={240:'Старые кости',244:'Койот',245:'Брамин',242:'Шляпочные',246:'Дождевики',247:'Колокольчатые'}
sheet=Image.new('RGB',(1200,640),(22,22,22));draw=ImageDraw.Draw(sheet)
for i,(asset,tile) in enumerate(tiles.items()):
    x=(i%3)*400;y=(i//3)*320
    draw.text((x+12,y+10),labels[asset],font=font,fill=(224,215,197))
    im=Image.open(OUT/f'decor-{asset}-tile-{tile}.png').convert('RGB')
    crop=im.crop((840,320,1080,496)).resize((384,282),Image.Resampling.NEAREST)
    sheet.paste(crop,(x+8,y+37))
sheet.save(QA/'six-types-in-game.png')
# Review all placements without changing the production sprite colors or light.
all_sheet=Image.new('RGB',(1200,((len(m['decoration_placements'])+3)//4)*220),(22,22,22));draw=ImageDraw.Draw(all_sheet)
for i,p in enumerate(m['decoration_placements']):
    x=(i%4)*300;y=(i//4)*220
    im=Image.open(OUT/f"decor-{p['asset_id']}-tile-{p['tile']}.png").convert('RGB')
    all_sheet.paste(im.crop((810,290,1110,490)),(x,y+20))
    draw.text((x+6,y+2),str(p['asset_id'])+' / '+str(p['tile']),font=small,fill=(210,210,200))
all_sheet.save(QA/'all-placements.png')
rows=[{k:int(v) for k,v in row.items()} for row in csv.DictReader((ROOT/'build/hd-world-pilot/preview/scattered-decor-v12-layout/walkable-layout.tsv').open(),delimiter='\t')]
coords={r['tile']:(r['x'],r['y']) for r in rows}
overview=Image.new('RGB',(1200,650),(22,22,24));draw=ImageDraw.Draw(overview)
minx=min(r['x'] for r in rows);miny=min(r['y'] for r in rows)
def point(x,y):return int((x-minx)*.49+30),int((y-miny)*.49+90)
for row in rows:
    x,y=point(row['x'],row['y']);draw.ellipse((x-3,y-2,x+3,y+2),fill=(63,63,66))
for p in m['decoration_placements']:
    x,y=point(*coords[p['tile']]);color=(193,164,113) if p['flat'] else (104,163,127)
    draw.ellipse((x-6,y-6,x+6,y+6),fill=color,outline=(0,0,0),width=1)
draw.text((30,20),'3 скопления костей · 14 групп грибов · 1 мусор',font=font,fill=(222,216,200))
draw.text((30,55),'Схема по доступным гексам; расстановка сохранена',font=small,fill=(160,160,160))
overview.save(QA/'placement-map.png')
review={'existing_images_and_metadata_unchanged':unchanged,'new_images':4,'new_spires_registered':False,
    'density':m['decoration_density'],'variant_counts':dict(counts),'disabled_decor_matches_v11_pixel_exact':True,
    'classic_matches_v11_pixel_exact':True,'qa_note':'Actual SDL capture crops without light correction; placement map is schematic.'}
(QA/'review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review))
