from pathlib import Path
import json,hashlib,shutil
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
B=R/'build/hd-wall-blender-natural-20261115';O=R/'assets/generated/v13ent-wall-blender/natural-v2-20261115'
LIVE=R/'runtime/hd-world-pilot';PREV=R/'work/hd-wall-blender-pilot-20261115'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (W/'baseline.json').exists()
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 previous=read(R/'build/hd-wall-blender-pilot-20261115/after-v4/manifest.json')
 assert sha(LIVE/'fallout-ce.exe')==previous['executable_sha256'].lower()
 compared=0
 for p in (PREV/'runtime/data/art').rglob('*'):
  if p.is_file() and p.name!='manifest.json':assert sha(p)==sha(LIVE/'data/art'/p.relative_to(PREV/'runtime/data/art')),p;compared+=1
 shutil.copytree(PREV/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copytree(R/'build/hd-wall-blender-pilot-20261115/after-v4',B/'before',ignore=shutil.ignore_patterns('*.bmp'))
 for n in ['pack.py','audit.py','review.py','install.py','test.ps1','rollback.ps1','scene.py']:
  t=(PREV/n).read_text(encoding='utf-8-sig').replace('hd-wall-blender-pilot-20261115','hd-wall-blender-natural-20261115').replace('v13ent-wall-blender/pilot-20261115','v13ent-wall-blender/natural-v2-20261115').replace('blender-corner-v1','blender-corner-v2').replace('after-v4','after-v1')
  t=t.replace('До: прежний HD','До: плиты Blender V1').replace('После: участок из Blender','После: естественная скала')
  (W/n).write_text(t,encoding='utf-8')
 shutil.copy2(R/'assets/generated/v13ent-wall-blender/pilot-20261115/reference-placements.json',O/'reference-placements.json')
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 save(B/'before-provenance.json',dict(source='build/hd-wall-blender-pilot-20261115/after-v4',same_executable=True,matched_art_files=compared))
 save(W/'task.json',dict(status='in progress',scope='Replace plate-like Blender corner with continuous natural rock; match neighboring stone',installed=False))
 print('Prepared natural rock revision; before verified against',compared,'current art files')
if __name__=='__main__':main()
