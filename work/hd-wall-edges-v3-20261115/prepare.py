from pathlib import Path
import hashlib,json,shutil

R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-geometry-kit/v3-edges-20261115'
B=R/'build/hd-wall-edges-v3-20261115'
LIVE=R/'runtime/hd-world-pilot'
OLD=R/'work/hd-wall-geometry-live-20261115'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (W/'baseline.json').exists(),'Existing workspace must be resumed, not reset'
 O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 shutil.copytree(OLD/'runtime',W/'runtime',ignore=shutil.ignore_patterns('*.bmp','*-test.exe','debug.log'))
 shutil.copytree(LIVE/'data/art',W/'runtime/data/art',dirs_exist_ok=True)
 shutil.copy2(LIVE/'fallout-ce.exe',W/'runtime/fallout-ce.exe')
 wrapper=(OLD/'test.ps1').read_text(encoding='utf-8-sig').replace('work/hd-wall-geometry-live-20261115/runtime','work/hd-wall-edges-v3-20261115/runtime')
 (W/'test.ps1').write_text(wrapper,encoding='utf-8-sig')
 master=Path('C:/Users/Administrator/.codex/generated_images/01a1dc00-496e-70e2-94b1-a7528ebaceb0/exec-8a5a4034-cc62-4fc9-ae35-178d6a7b7860.png')
 shutil.copy2(master,O/'edge-relief-imagegen.png')
 files={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.log','.bmp']}
 save(W/'baseline.json',dict(runtime=str(LIVE),files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')))
 save(O/'generation.json',dict(tool='built-in image_gen',mode='edit',input='assets/generated/v13ent-wall-geometry-kit/v2-registered-20261115/relief-atlas.png',native_output=str(master),output_sha256=sha(master),seed=None,purpose='Finish the upper relief in chipped receding crown planes, keeping the lower 75 percent and neutral stone appearance. Upper border meets dark RGB34 cutaway. Full prompt: generation-prompt.txt.'))
 save(W/'task.json',dict(status='in progress',component='wall-edges-v3',scope='Common top and end boundaries; same EXE, object positions, alpha and collision',installed=False))
 print('Prepared separate runtime and recorded current baseline')
if __name__=='__main__':main()
