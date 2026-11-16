from pathlib import Path
import shutil,json,hashlib
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-geometry-kit/v4-crown-20261115';B=R/'build/hd-wall-crown-v4-20261115'
LIVE=R/'runtime/hd-world-pilot';PREV=R/'work/hd-wall-edges-v3-20261115'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (W/'baseline.json').exists(),'Resume existing workspace'
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 shutil.copytree(PREV/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 text=(PREV/'test.ps1').read_text(encoding='utf-8-sig').replace('work/hd-wall-edges-v3-20261115/runtime','work/hd-wall-crown-v4-20261115/runtime')
 (W/'test.ps1').write_text(text,encoding='utf-8-sig')
 gen=Path('C:/Users/Administrator/.codex/generated_images/01a1dc00-496e-70e2-94b1-a7528ebaceb0')
 refs=[('exec-a15db266-561a-41b0-9072-5114599b222a.png','wall-material.png'),('exec-cbc07e64-59ff-414c-a829-b464fc9de67d.png','cap-material.png')]
 for src,dest in refs:shutil.copy2(gen/src,O/dest)
 save(O/'generation.json',dict(tool='built-in image_gen',seed=None,outputs=[dict(native=str(gen/src),saved=dest,sha256=sha(O/dest)) for src,dest in refs],prompts='generation-prompts.txt',reference_geometry='assets/generated/v13ent-wall-geometry-kit/v2-registered-20261115/relief-atlas.png',reference_material='assets/hd/v13ent/v14-campfire-x4/art/scenery/rock03.frm.png'))
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 save(W/'task.json',dict(status='in progress',component='wall-crown-v4',scope='Visible stone cutaway plus crisp wall crown, unchanged alpha, registration and EXE',installed=False))
 print('Prepared crown prototype runtime and baseline')
if __name__=='__main__':main()
