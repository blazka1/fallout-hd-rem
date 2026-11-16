from pipeline import *
import subprocess
BACK=R/'build/backups/before-wall-grey-match-20261116'
def main():
 running=subprocess.run(['powershell','-NoProfile','-Command',"(Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue | Measure-Object).Count"],capture_output=True,text=True,check=True);assert int(running.stdout.strip())==0,'Close Fallout before integration'
 rows=read(O/'images.json');test=read(B/'after-v1/manifest.json');audit=read(B/'asset-audit.json');comp=read(B/'comparison.json');baseline=read(W/'baseline.json')
 assert test['result']['passed']==1119 and test['result']['failed']==0
 assert comp['classic_all_exact'] and len(comp['classic_frames'])==18
 assert audit['alpha_exact_before_all'] and audit['registration_files_unchanged'] and audit['wall_curve_exact'] and audit['all_neutral_grey'] and audit['reference_rocks_unchanged']
 # Reuse the previously verified test-only executable. It changes one assertion,
 # and its game/rendering source is identical to the installed stock executable.
 previous_test=read(R/'build/hd-wall-original-restore-20261116/native-check/manifest.json')
 assert test['executable_sha256']==previous_test['executable_sha256']
 assert sha(LIVE/'fallout-ce.exe')==baseline['exe_sha256']==sha(W/'runtime/fallout-ce.exe')
 root=LIVE/'data/art/hd/world-pilot';names=[r['file'] for r in rows]+['manifest.json'];changed={'data/art/hd/world-pilot/'+n for n in names}
 for row in rows:
  assert sha(root/row['file'])==row['before_sha256'],('Concurrent change',row['file']);assert sha(D/row['file'])==row['sha256']
 for f in (LIVE/'data/art').rglob('*'):
  if f.is_file():
   rel=str(f.relative_to(LIVE)).replace('\\','/')
   if rel not in changed:assert sha(f)==sha(W/'runtime'/rel),('Refresh and retest newer shared art',rel)
 assert not (BACK/'state.json').exists()
 protected={str(f.relative_to(LIVE)).replace('\\','/'):sha(f) for f in LIVE.rglob('*') if f.is_file() and f.suffix.lower() not in ['.bmp','.log']}
 m=read(root/'manifest.json');BACK.mkdir(parents=True);PKG.mkdir(parents=True,exist_ok=True);files=[]
 for name in names:
  shutil.copy2(root/name,BACK/name);files.append(dict(name=name,before_sha256=sha(root/name)))
 save(BACK/'state.json',dict(status='backed up',component_before='original-seed-qwen-v1',files=files))
 for row in rows:shutil.copy2(D/row['file'],root/row['file']);shutil.copy2(R/row['png'],PKG/Path(row['png']).name)
 for n in ['plan.json','targets.json','reference-measurements.json','rock-reference.png']:shutil.copy2(O/n,PKG/n)
 for n in ['pipeline.py','finish.py','review.py','install.py','README.txt','rollback.ps1']:shutil.copy2(W/n,PKG/n)
 byfile={r['file']:r for r in rows}
 for a in m['assets']:
  if a['filename'] in byfile:
   row=byfile[a['filename']];png=PKG/Path(row['png']).name
   a.update(runtime_file_sha256=row['sha256'],source_png=str(png),source_png_sha256=sha(png),appearance_component='original-seed-qwen-grey-v2',decoded_rgba_sha256=hashlib.sha256((D/row['file']).read_bytes()[20:]).hexdigest())
 m['wall_geometry'].update(component='original-seed-qwen-grey-v2',package=str(PKG.relative_to(R)),report=str((B/'after-v1/manifest.json').relative_to(R)),test_only_exe_not_installed=True,alpha_preserved=True)
 m['wall_geometry']['grey_match']=dict(walls='shared Rec709 neutral grey, gain 1.18 and offset 4/255',ceiling='original SeedVR2 x4 -> Qwen 2.1 with neutral rock reference; bounded interior contribution, exact original alpha and corrected edge colors',alpha_exact_previous=True,geometry_unchanged=True,reference='current installed grey boulders and formations',source_count=65)
 m['wall_geometry'].pop('installed_exe_capture_report',None)
 m.setdefault('component_patches',[]).append(dict(component='original-seed-qwen-grey-v2',package=str(PKG.relative_to(R)),report=str((B/'after-v1/manifest.json').relative_to(R)),images=len(rows),geometry_unchanged=True))
 save(root/'manifest.json',m)
 for f in files:f['installed_sha256']=sha(root/f['name'])
 save(BACK/'state.json',dict(status='installed',component_before='original-seed-qwen-v1',files=files))
 protected_count=0
 for rel,hsh in protected.items():
  if rel not in changed:assert sha(LIVE/rel)==hsh,rel;protected_count+=1
 for row in rows:assert sha(root/row['file'])==row['sha256']
 receipt=dict(status='installed and verified',component='original-seed-qwen-grey-v2',images=rows,checks=test['result'],test_exe_sha256=test['executable_sha256'],installed_exe_unchanged=True,installed_exe_sha256=sha(LIVE/'fallout-ce.exe'),test_source_provenance='build/hd-wall-original-restore-20261116/test-only-source-change.json',audit=audit,comparison=comp,backup=str(BACK.relative_to(R)),other_runtime_files_unchanged=protected_count,generated=str(O.relative_to(R)))
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='images'})
 print('INSTALLED',len(rows),'neutral-grey images; exact prior alpha; unchanged EXE and',protected_count,'other runtime files')
if __name__=='__main__':main()
