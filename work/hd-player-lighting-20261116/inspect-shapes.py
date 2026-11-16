from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'assets/hd/player-male-vault13/lighting-v2-x4'
RUN=ROOT/'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
entries=json.loads((PKG/'manifest.json').read_text())['entries']
worst=sorted(entries,key=lambda r:r['silhouette_iou_previous_hd'])[:3]
sheet=Image.new('RGB',(640,960),(90,88,80));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
for row,r in enumerate(worst):
    for col,p in enumerate([Path(r['hd_source']),PKG/r['png']]):
        im=Image.open(p).convert('RGBA')
        sheet.paste(im,(col*320+(320-im.width)//2,row*320+310-im.height),im)
        label=('Before' if col==0 else 'Relit')+f" / {r['stem']} / IoU {r['silhouette_iou_previous_hd']:.3f}"
        draw.text((col*320+6,row*320+8),label,font=font,fill='white')
sheet.save(RUN/'preview/lowest-silhouette-iou.png')
print([(r['stem'],r['silhouette_iou_previous_hd']) for r in worst])
