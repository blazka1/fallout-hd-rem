from pathlib import Path
import json,hashlib,shutil,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as nd
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-blender/cave-v3-20261115'
B=R/'build/hd-wall-blender-cave-20261115'
LIVE=R/'runtime/hd-world-pilot';D=W/'runtime/data/art/hd/world-pilot'
SRC=R/'assets/generated/v13ent-cave/v1-20261111/sources'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):
 b=p.read_bytes();m,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(h,w,4).copy()
def pack(p,a):p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def main():
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 assert not (W/'baseline.json').exists()
 previous=R/'work/hd-wall-blender-natural-20261115/runtime'
 # Use the existing isolated data/configuration, refreshed from current art and EXE.
 shutil.copytree(previous,W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 old=R/'work/hd-wall-blender-natural-20261115'
 text=(old/'test.ps1').read_text(encoding='utf-8-sig').replace('hd-wall-blender-natural-20261115','hd-wall-blender-cave-20261115')
 (W/'test.ps1').write_text(text,encoding='utf-8')
 same=all(sha(p)==sha(LIVE/'data/art'/p.relative_to(previous/'data/art')) for p in (previous/'data/art').rglob('*') if p.is_file() and p.name!='manifest.json')
 if same and sha(previous/'fallout-ce.exe')==sha(LIVE/'fallout-ce.exe'):
  shutil.copytree(R/'build/hd-wall-blender-natural-20261115/after-v1',B/'before',ignore=shutil.ignore_patterns('*.bmp'))
  save(B/'before-provenance.json',dict(source='build/hd-wall-blender-natural-20261115/after-v1',all_art_and_exe_identical=True))
 shutil.copy2(R/'assets/generated/v13ent-wall-blender/natural-v2-20261115/reference-rock-detail.png',O/'reference-rock-detail.png')
 save(W/'task.json',dict(status='in progress',scope='Full cave natural Blender geometry with shared rock material and crown',installed=False))
 print('Prepared',len(files),'baseline files; before identical',same)
if __name__=='__main__':main()
