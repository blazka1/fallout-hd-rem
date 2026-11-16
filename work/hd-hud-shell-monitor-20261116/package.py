"""Package the approved Qwen HUD, with a deterministic SKILLDEX UI label fix."""
from pathlib import Path
import hashlib,json,struct
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/generated/hud-shell-monitor/seed-qwen-v1-20261116/qwen/qwen-master.png'
OUT=ROOT/'assets/hd/hud-panel/seed-qwen-v1'
OUT.mkdir(parents=True,exist_ok=True)
im=Image.open(SOURCE).convert('RGB');assert im.size==(3840,600)
original=np.asarray(im).copy()
# The approved artwork remains untouched. Reuse its clean blue strip inside
# the existing nameplate; text is UI typography, generated deterministically.
box=(558*6,13*6,624*6,21*6)
strip=im.crop((558*6,11*6,624*6,13*6)).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.BICUBIC)
im.paste(strip,(box[0],box[1]))
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',72)
bb=font.getbbox('SKILLDEX')
mask=Image.new('L',(bb[2]-bb[0]+4,bb[3]-bb[1]+4))
ImageDraw.Draw(mask).text((2-bb[0],2-bb[1]),'SKILLDEX',font=font,fill=255)
mask=mask.resize((350,38),Image.Resampling.LANCZOS)
x=box[0]+(box[2]-box[0]-350)//2;y=box[1]+(box[3]-box[1]-38)//2
im.paste((13,24,34),(x+1,y+1,x+351,y+39),mask)
im.paste((178,190,204),(x,y,x+350,y+38),mask)
im=im.convert('RGBA');im.putalpha(255)
im.save(OUT/'shell-monitor.png')
data=b'F1HD'+struct.pack('<IIII',1,3840,600,6)+im.tobytes()
(OUT/'shell-monitor.rgba').write_bytes(data)
changed=np.any(np.asarray(im)[:,:,:3]!=original,axis=2)
guard=np.ones((600,3840),bool);guard[box[1]:box[3],box[0]:box[2]]=False
assert not changed[guard].any()
im.crop((548*6,0,640*6,32*6)).save(OUT/'skilldex-detail.png')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(dict(status='approved-art-prepared-for-integration',source=str(SOURCE),
 source_sha256=sha(SOURCE),native=[640,100],master=[3840,600],scale=6,
 label='SKILLDEX',label_repair_box=list(box),rgb_outside_label_unchanged=True,
 source_alpha='Qwen 241..255 normalized to opaque for the HUD base',
 png_sha256=sha(OUT/'shell-monitor.png'),runtime_asset_sha256=sha(OUT/'shell-monitor.rgba')),
 ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(OUT)
