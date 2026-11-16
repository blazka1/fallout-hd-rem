"""Assemble actual SDL comparison captures. Does not process game assets."""
from pathlib import Path
import hashlib, json, html
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-cave-distribution-20261115/review'
SRC=OUT.parent/'enabled-v3'
OUT.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
pairs=[('entrance','new-form-224'),('rocks','new-form-232'),('formations','new-form-237')]
records=[]
for label,name in pairs:
    files=[SRC/(name+'-previous-hd.png'),SRC/(name+'-hd.png')]
    sheet=Image.new('RGB',(1920,584),'#17191b')
    draw=ImageDraw.Draw(sheet)
    for col,(path,title) in enumerate(zip(files,['Previous HD / прежняя раскладка','Balanced mix / равномерная смесь'])):
        image=Image.open(path).convert('RGB')
        sheet.paste(image.resize((960,540),Image.Resampling.LANCZOS),(col*960,44))
        draw.text((col*960+18,9),title,font=font,fill='#eee8d6')
    sheet.save(OUT/(label+'-comparison.png'))
    records.append(dict(file=label+'-comparison.png',sources=[dict(file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],processing='same 50% preview scale; no color correction'))

distribution=json.loads((ROOT/'assets/hd/v13ent/cave-distribution-v1/distribution.json').read_text(encoding='utf-8'))
cards=[]
for asset in range(224,239):
    name=f'new-form-{asset}'
    cards.append(f'<section><h2>Форма {asset}</h2><div class="pair"><figure><img src="../enabled-v3/{name}-previous-hd.png"><figcaption>Прежняя HD</figcaption></figure><figure><img src="../enabled-v3/{name}-hd.png"><figcaption>Новая раскладка</figcaption></figure></div></section>')
page='''<!doctype html><meta charset="utf-8"><title>Пещера — равномерная смесь форм</title><style>body{background:#17191b;color:#e8e1d1;font:17px Arial;margin:28px}h1{font-size:28px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}figure{margin:0}img{width:100%}figcaption{padding:8px}section{margin-top:32px}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #555}</style><h1>Пещера: прежняя HD и новая раскладка</h1><p>116 исходных мест: 40 прежних форм, 76 новых. Карта и блокеры сохранены. Все изображения ниже — реальные SDL-кадры одного проверочного прогона.</p><table><tr><th>Группа</th><th>Мест</th><th>Старых</th><th>Новых</th></tr><tr><td>Камни</td><td>107</td><td>36</td><td>71</td></tr><tr><td>Сталагмиты</td><td>7</td><td>3</td><td>4</td></tr><tr><td>Колонны</td><td>2</td><td>1</td><td>1</td></tr></table><p>Квота каждого вида камней: floor(107 / 18) = 5, остаток 17 даёт по одному дополнительному месту 17 видам. Фиксированный seed 15112026; одинаковые формы распределены с приоритетом расстояния между ними. Из 16 новых форм в этой раскладке используются 15: для двух новых колонн и сохранения старых не хватает двух исходных мест.</p>'''+''.join(cards)
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT/'index.html')
