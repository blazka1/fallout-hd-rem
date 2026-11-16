"""Read-only comparison previews of selected candidates, never source editing."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'assets/generated/v13ent-vault/materials-v2-20261114';OUT=ROOT/'build/hd-vault-materials-v2/review';OUT.mkdir(parents=True,exist_ok=True)
rows={r['asset_id']:r for r in json.loads((ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json').read_text())['assets']}
# Freeze "before" to the preparation inputs, even after the runtime is installed.
for kind in ['walls','frame','door','floor']:
 sp=RUN/kind/'prepared/specs.json'
 if sp.exists():
  for a in json.loads(sp.read_text()):rows[a['id']]['source_png']=a['alpha']
def board(images,labels,name,maxw=900):
 w=max(im.width for im in images);ht=max(im.height for im in images);canvas=Image.new('RGB',(w*len(images),ht+30),(35,35,35));d=ImageDraw.Draw(canvas)
 for i,im in enumerate(images):
  canvas.paste(im,(w*i,30),im.getchannel('A') if im.mode=='RGBA' else None);d.text((w*i+8,8),labels[i],fill='white')
 if canvas.width>maxw:canvas=canvas.resize((maxw,round(canvas.height*maxw/canvas.width)),Image.Resampling.LANCZOS)
 canvas.save(OUT/name)
for kind in ['walls','frame','door','floor']:
 p=RUN/kind/'prepared'
 if not (p/'specs.json').exists():continue
 specs=json.loads((p/'specs.json').read_text())
 if not all((p/f"asset-{a['id']:03}.png").exists() for a in specs):continue
 if kind=='walls':
  spec=json.loads((ROOT/'assets/generated/v13ent-vault/v1-rust-20261112/wall-input-atlas/run.json').read_text());canvas=[]
  ids={r.get('original_resource'):i for i,r in rows.items()}
  for new in [False,True]:
   im=Image.new('RGBA',tuple(spec['register_size']))
   for item in sorted(spec['placements'],key=lambda a:(a['anchor_y'],a['x'],a['id'])):
    i=ids[item['source']];source=p/f'asset-{i:03}.png' if new else Path(rows[i]['source_png']);tile=Image.open(source).convert('RGBA');im.alpha_composite(tile,tuple(item['crop_x4'][:2]))
   im.save(OUT/('walls-after.png' if new else 'walls-before.png'));canvas.append(im)
  board(canvas,['Before','After'],'walls-comparison.png',1400)
 elif kind=='door':
  frames=[]
  for a in specs:
   before=Image.open(rows[a['id']]['source_png']).convert('RGBA');after=Image.open(p/f"asset-{a['id']:03}.png").convert('RGBA')
   c=Image.new('RGB',(1512,628),(35,35,35));c.paste(before,(0,0),before);c.paste(after,(756,0),after);c=c.resize((1000,415),Image.Resampling.LANCZOS);frames.append(c)
  frames[0].save(OUT/'door-animation.gif',save_all=True,append_images=frames[1:],duration=160,loop=0)
  frames[0].save(OUT/'door-closed.png');frames[-1].save(OUT/'door-open.png')
  contact=Image.new('RGB',(1500,747),(35,35,35));d=ImageDraw.Draw(contact)
  for i,fr in enumerate(frames):
   x=(i%3)*500;y=(i//3)*149;contact.paste(fr.resize((500,124)),(x,y+25));d.text((x+8,y+6),'Frame '+str(i)+' | before / after',fill='white')
  contact.save(OUT/'door-contact.png')
 else:
  a=specs[0];images=[Image.open(rows[a['id']]['source_png']).convert('RGBA'),Image.open(p/f"asset-{a['id']:03}.png").convert('RGBA')]
  if kind=='frame':
   refined=RUN/'frame/refined-v2/asset-016.png'
   if refined.exists():images[1]=Image.open(refined).convert('RGBA')
   images=[im.crop((192,448,544,896)) for im in images]
  elif kind=='floor' and (RUN/'floor/clean-v2/asset-088.png').exists():images[1]=Image.open(RUN/'floor/clean-v2/asset-088.png').convert('RGBA')
  board(images,['Before','After'],kind+'-comparison.png')
 print('QA ready',kind)
