"""Point installation with rollback copies and protected-runtime verification."""
import sys,struct,shutil,subprocess,re,json
from pathlib import Path
from PIL import Image
import numpy as np
import prepare as q
p=q.p;R=q.R;OUT=q.OUT;B=R/'build/hd-cave-seams-20261115';BACK=R/'build/backups/before-cave-seams-20261115';RT=R/'runtime/hd-world-pilot';DATA=RT/'data/art/hd/world-pilot';PACK=R/'assets/hd/v13ent/cave-seams-v1'

def idle():
 result=subprocess.run(['powershell','-NoProfile','-Command','@(Get-Process -Name fallout-ce,fallout-seam-test,fallout-wall-test -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True,check=True)
 assert result.stdout.strip()=='0','Fallout is running'

def stage(kind):
 idle();PACK.mkdir(parents=True,exist_ok=True);manifest=p.read(PACK/'manifest.json') if (PACK/'manifest.json').exists() else {'status':'staged for review','records':[]}
 rows=p.read(OUT/kind/'records.json')
 for a in rows:
  id=a['id'];path=OUT/kind/('asset-%03d.png'%id);oldpath=OUT/'inputs'/('asset-%03d.png'%id);im=Image.open(path).convert('RGBA');old=np.array(Image.open(oldpath).convert('RGBA'));new=np.array(im)
  assert old.shape==new.shape and np.array_equal(old[:,:,3],new[:,:,3]),(id,'alpha')
  diff=np.any(old!=new,axis=2);assert diff.sum()>0,id
  if 'protected_lower_from' in a:assert not diff[a['protected_lower_from']:].any(),id
  previous=next((x for x in manifest['records'] if x['id']==id),None)
  expected=previous['runtime_sha256'] if previous else p.sha(BACK/a['file']);assert p.sha(DATA/a['file'])==expected,a['file']
  target=PACK/a['file'];target.write_bytes(struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes());shutil.copy2(path,PACK/('asset-%03d.png'%id));shutil.copy2(target,DATA/a['file'])
  record=dict(**a,png='asset-%03d.png'%id,source_png=str(path.relative_to(R)),png_sha256=p.sha(path),runtime_sha256=p.sha(target),alpha_exact=True,changed_pixels=int(diff.sum()))
  manifest['records']=[x for x in manifest['records'] if x['id']!=id]+[record]
 p.save(PACK/'manifest.json',manifest);print('Staged',kind,len(rows),'assets',flush=True)

def finish():
 idle();manifest=p.read(PACK/'manifest.json');exe=p.sha(RT/'fallout-seam-test.exe');checks={}
 for n in ['world','terminal','menu']:
  m=p.read(B/n/'manifest.json');result=m.get('result',m);assert m['executable_sha256'].lower()==exe and result['failed']==0,n
  checks[n]=dict(passed=result['passed'],failed=0)
 before=p.read(BACK/'runtime-before.json');allowed={str((DATA/a['file']).relative_to(R)) for a in manifest['records']}
 cfg=RT/'fallout.cfg';norm=lambda x:re.sub(rb'(?m)^splash=\d+',b'splash=0',x)
 assert norm(cfg.read_bytes())==norm((BACK/'fallout.cfg').read_bytes())
 for file,h in before.items():
  if file not in allowed and file!=str(cfg.relative_to(R)):assert p.sha(R/file)==h,file
 runtime=p.read(DATA/'manifest.json');byid={a['asset_id']:a for a in runtime['assets']}
 for a in manifest['records']:
  assert p.sha(DATA/a['file'])==a['runtime_sha256'];row=byid[a['id']]
  import hashlib
  row.update(source_png=str(PACK/a['png']),source_png_sha256=p.sha(PACK/a['png']),runtime_file_sha256=a['runtime_sha256'],decoded_rgba_sha256=hashlib.sha256((DATA/a['file']).read_bytes()[20:]).hexdigest())
 runtime['component_patches'].append(dict(component='cave-seams-v1',package=str(PACK),changed_assets=[a['id'] for a in manifest['records']],alpha_unchanged=True))
 shutil.copy2(RT/'fallout-seam-test.exe',RT/'fallout-ce.exe');shutil.copy2(BACK/'fallout.cfg',cfg);p.save(DATA/'manifest.json',runtime)
 receipt=dict(status='installed-and-verified',checks=checks,executable_sha256=exe,assets=[a['id'] for a in manifest['records']],protected_existing_files=sum(p.sha(R/f)==h for f,h in before.items()),review=str((B/'review/index.html').relative_to(R)),code_changes='optional diagnostic captures in test harness only',game_geometry_changed=False)
 p.save(B/'integration.json',receipt);p.save(R/'work/hd-cave-seams-20261115/task.json',receipt);manifest['status']='installed-and-verified';p.save(PACK/'manifest.json',manifest);print(json.dumps(receipt),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='finish':finish()
 else:stage(sys.argv[1])
