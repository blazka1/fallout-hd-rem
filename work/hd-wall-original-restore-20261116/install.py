from pipeline import *
BACK=R/'build/backups/before-original-seed-qwen-v1-20261116'
def main():
 import subprocess
 running=subprocess.run(['powershell','-NoProfile','-Command',"(Get-Process -Name 'fallout*' -ErrorAction SilentlyContinue | Measure-Object).Count"],capture_output=True,text=True,check=True)
 assert int(running.stdout.strip())==0,'Close Fallout before installing new images'
 rows=read(O/'images.json');stock=read(B/'after-v1/manifest.json');test=read(B/'native-check/manifest.json');equivalence=read(B/'test-render-equivalence.json');comp=read(B/'comparison.json');audit=read(B/'asset-audit.json')
 assert test['result']['passed']==1119 and test['result']['failed']==0
 assert equivalence['all_exact'] and equivalence['frames']==117 and len(equivalence['sampled_views_not_paired'])==38
 assert comp['classic_all_exact'] and len(comp['classic_frames'])==18
 assert audit['canonical_alpha_exact_original_all'] and audit['runtime_native_alpha_exact_images']==536 and audit['source_contexts_pixel_exact'] and audit['exe_unchanged']
 assert sha(LIVE/'fallout-ce.exe')==stock['executable_sha256'].lower()==sha(W/'runtime/fallout-ce.exe')
 root=LIVE/'data/art/hd/world-pilot';names=[r['file'] for r in rows]+['manifest.json']
 assert not (BACK/'state.json').exists(),'Installation already begun; inspect receipt before resume'
 changed={'data/art/hd/world-pilot/'+n for n in names}
 for r in rows:
  assert sha(root/r['file'])==r['before_sha256'],('Later change',r['file'])
  assert sha(D/r['file'])==r['sha256']
 for p in (LIVE/'data/art').rglob('*'):
  if p.is_file():
   rel=str(p.relative_to(LIVE)).replace('\\','/')
   if rel not in changed:assert sha(p)==sha(W/'runtime'/rel),('Refresh newer shared art and retest',rel)
 protected={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.bmp','.log']}
 m=read(root/'manifest.json');BACK.mkdir(parents=True);PKG.mkdir(parents=True,exist_ok=True);files=[]
 for name in names:
  shutil.copy2(root/name,BACK/name);files.append(dict(name=name,before_sha256=sha(root/name)))
 save(BACK/'state.json',dict(status='backed up',component_before='blender-cave-v3',files=files))
 for r in rows:
  shutil.copy2(D/r['file'],root/r['file']);shutil.copy2(R/r['png'],PKG/Path(r['png']).name)
 for n in ['selected-sources.json','plan.json','sources.json','targets.json','provenance.json']:shutil.copy2(O/n,PKG/n)
 for n in ['pipeline.py','assemble.py','review.py','install.py','README.txt','rollback.ps1']:shutil.copy2(W/n,PKG/n)
 byfile={r['file']:r for r in rows}
 for a in m['assets']:
  if a['filename'] in byfile:
   r=byfile[a['filename']];png=PKG/Path(r['png']).name
   a.update(runtime_file_sha256=r['sha256'],source_png=str(png),source_png_sha256=sha(png),appearance_component='original-seed-qwen-v1',decoded_rgba_sha256=hashlib.sha256((D/r['file']).read_bytes()[20:]).hexdigest(),alpha_exact_original_nearest_neighbor=True,alpha_values=[0,255])
   if r['kind']=='door':a.update(alpha_exact_original_nearest_neighbor=False,original_alpha_reused=False,alpha_values=np.unique(decode(D/r['file'])[:,:,3]).tolist(),alpha_note='native ca036 alpha clipped by the user-approved door clearance')
 m['wall_geometry'].update(component='original-seed-qwen-v1',package=str(PKG.relative_to(R)),alpha_preserved=True,alpha_exact_original=True,report=str((B/'native-check/manifest.json').relative_to(R)),installed_exe_capture_report=str((B/'after-v1/manifest.json').relative_to(R)),test_only_exe_not_installed=True,geometry_only=False,placement_images=417,cap_images=9,approved_door_preserved=False,door_restored_to_original=True,door_clearance_preserved=True,door_alpha_exception='native alpha intersected with approved A clearance around metal frame')
 for key in ['blender_corner_pilot','blender_cave']:
  if key in m['wall_geometry']:m['wall_geometry'][key]['superseded_by']='original-seed-qwen-v1'
 m['wall_geometry']['original_restoration']=dict(source_walls=62,source_cap_tiles=3,pipeline='SeedVR2 x4 -> Qwen Image 2.1 + original Canny -> original color/alpha/registration',images=len(rows),geometry_redesigned=False,executable_changed=False,prior_blender_package='assets/hd/v13ent/blender-cave-v3')
 m.setdefault('component_patches',[]).append(dict(component='original-seed-qwen-v1',package=str(PKG.relative_to(R)),report=str((B/'native-check/manifest.json').relative_to(R)),source_sprites=65,images=len(rows),door_clearance_retained=True))
 save(root/'manifest.json',m)
 for f in files:f['installed_sha256']=sha(root/f['name'])
 save(BACK/'state.json',dict(status='installed',component_before='blender-cave-v3',files=files))
 count=0
 for rel,hsh in protected.items():
  if rel not in changed:assert sha(LIVE/rel)==hsh,('Unexpected modification',rel);count+=1
 for r in rows:assert sha(root/r['file'])==r['sha256']
 receipt=dict(status='installed and verified',component='original-seed-qwen-v1',images=rows,source_sprites=65,wall_sources=62,cap_sources=3,checks=test['result'],test_render_equivalence=equivalence,legacy_test_result=stock['result'],test_source_change=read(B/'test-only-source-change.json'),audit=audit,comparison=comp,exe_unchanged=True,exe_sha256=sha(LIVE/'fallout-ce.exe'),other_runtime_files_unchanged=count,backup=str(BACK.relative_to(R)),blender_preserved='assets/hd/v13ent/blender-cave-v3',generated=str(O.relative_to(R)))
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='images'})
 print('INSTALLED',len(rows),'images; unchanged EXE and',count,'other runtime files; archived prior Blender runtime',BACK)
if __name__=='__main__':main()
