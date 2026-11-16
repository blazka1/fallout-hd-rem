"""Read-only HUD resource audit; exports originals and diagnostic sheets."""
from pathlib import Path
import hashlib, io, json, re, struct, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/reference/hud-panel-audit-20261115'
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline'))
from fallout_assets import Assets, decode_frm, palette_rgb, png_indexed, lst_names, write_bytes

assets = Assets([ROOT / 'FALLOUT (extract.me)/MASTER.DAT'])
names = lst_names(assets.read('art/intrface/intrface.lst'))
palette = palette_rgb(assets.read('color.pal'))
ids = [16,47,46,18,17,6,7,13,10,59,58,57,56,32,31,73,82,83,84,85,
       104,105,106,107,108,109,110,287,288,289,290,291,292,294,117,45,44,43,40,126]
records, images = [], {}
for index in ids:
    name = names[index]
    path = 'art/intrface/' + name
    raw = assets.read(path)
    version = struct.unpack_from('>I', raw)[0]
    assert version in (3,4), (name, version)
    # CE reads the same header/subframe fields for v3 and v4. Only the
    # in-memory parser copy changes; archived original bytes remain intact.
    meta, directions = decode_frm(raw if version == 4 else b'\0\0\0\4' + raw[4:])
    meta['version'] = version
    write_bytes(OUT, 'raw/' + path, raw)
    frames = directions[0]
    for number, frame in enumerate(frames):
        png = png_indexed(frame.width, frame.height, frame.pixels, palette, index != 16)
        write_bytes(OUT, f'png/{Path(name).stem}-{number:02}.png', png)
        if number == 0:
            images[index] = Image.open(io.BytesIO(png)).convert('RGBA')
    records.append(dict(id=index, resource=path, sha256=hashlib.sha256(raw).hexdigest(),
                        width=frames[0].width,height=frames[0].height, metadata=meta))

font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
groups = [
    (1, 'Корпус и экран журнала', (0,0,209,100)),
    (2, 'INV / настройки / смена руки', (209,0,247,100)),
    (3, 'Оружие, действие, AP и боезапас', (247,0,468,100)),
    (4, 'HP и AC', (468,28,520,100)),
    (5, 'SKILLDEX / MAP / CHA / PIP', (520,0,580,100)),
    (6, 'Боевая крышка и кнопки', (580,28,640,100)),
]
sheet = Image.new('RGB', (1600, 560), '#202326')
sheet.paste(images[16].convert('RGB').resize((1536,240),Image.Resampling.NEAREST), (32,45))
d = ImageDraw.Draw(sheet)
d.text((32,12), 'Оригинальный фон HUD 640×100 — области для работы (не готовые HD-текстуры)',font=font,fill='white')
colors = ['#66d9ef','#f7b267','#b4dc7f','#ed8bb8','#c5a6ff','#efc94c']
for (n,label,box),color in zip(groups,colors):
    x0,y0,x1,y1 = [round(v*2.4) for v in box]
    d.rectangle((32+x0,45+y0,32+x1-1,45+y1-1),outline=color,width=3)
    d.rectangle((32+x0,45+y0,55+x0,70+y0),fill='#17191b')
    d.text((37+x0,46+y0),str(n),font=font,fill=color)
    d.text((32,305+(n-1)*36),f'{n}. {label}',font=font,fill=color)
sheet.save(OUT/'panel-map.png')

tiles = [r for r in records if r['id'] != 16]
contact = Image.new('RGB',(1440, ((len(tiles)+3)//4)*150),'#24272b')
d = ImageDraw.Draw(contact)
for i,r in enumerate(tiles):
    x,y=(i%4)*360,(i//4)*150
    d.text((x+10,y+8),f"{r['id']}: {Path(r['resource']).name}",font=small,fill='white')
    d.text((x+10,y+29),f"{r['width']}×{r['height']}, кадров: {r['metadata']['frame_count']}",font=small,fill='#b0b8c0')
    im=images[r['id']]
    scale=min(3,340/im.width,95/im.height)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST)
    contact.paste(im,(x+10,y+52),im)
contact.save(OUT/'components.png')
(OUT/'manifest.json').write_text(json.dumps({'source':'MASTER.DAT; mapping checked against intface.cc and display.cc',
    'resources':records,'note':'PNG frames are original palette exports; sheets use nearest-neighbor for inspection, not AI upscaling.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'id':r['id'],'name':r['resource'],'size':[r['width'],r['height']],'frames':r['metadata']['frame_count']} for r in records],ensure_ascii=False))
