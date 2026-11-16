from pathlib import Path
import json,hashlib,shutil
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
B=R/'build/hd-wall-blender-pilot-20261115';O=R/'assets/generated/v13ent-wall-blender/pilot-20261115'
LIVE=R/'runtime/hd-world-pilot';PREV=R/'work/hd-wall-crown-v4-20261115'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (W/'baseline.json').exists(),'Workspace already prepared'
 B.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
 shutil.copytree(PREV/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 text=(PREV/'test.ps1').read_text(encoding='utf-8-sig').replace('work/hd-wall-crown-v4-20261115/runtime','work/hd-wall-blender-pilot-20261115/runtime')
 (W/'test.ps1').write_text(text,encoding='utf-8-sig')
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 inv=read(R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115/inventory.json')
 src=R/'assets/generated/v13ent-cave/v1-20261111/sources';sources={a['path']:a for a in read(src/'manifest.json')['assets']}
 box=[4112,225,4470,535];scale=3;im=Image.new('RGBA',((box[2]-box[0])*scale,(box[3]-box[1])*scale),(24,24,27,255))
 ps=[p for p in inv['placements'] if p['x']<box[2] and p['x']+p['width']>box[0] and p['y']<box[3] and p['y']+p['height']>box[1]]
 for p in ps:
  a=Image.open(src/sources[p['source']]['rgba_png']).convert('RGBA').resize((p['width']*scale,p['height']*scale),Image.Resampling.NEAREST)
  im.alpha_composite(a,((p['x']-box[0])*scale,(p['y']-box[1])*scale))
 im.save(B/'original-section.png');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
 for p in ps:
  x=(p['x']-box[0])*scale;y=(p['y']-box[1])*scale
  d.rectangle((x,y,x+p['width']*scale-1,y+p['height']*scale-1),outline=(130,80,50));d.text((x,y+12),str(p['id']),font=font,fill='yellow')
 im.save(B/'original-section-ids.png');save(O/'reference-placements.json',dict(box=box,placements=ps))
 save(W/'task.json',dict(status='in progress',scope='One Blender-authored cave wall corner and crown',installed=False))
 print('Prepared isolated current runtime, baseline and reference section')
if __name__=='__main__':main()
