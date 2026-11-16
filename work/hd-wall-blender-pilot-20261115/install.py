from pack import *
PKG=R/'assets/hd/v13ent/blender-corner-v1';BACK=R/'build/backups/before-blender-corner-v1-20261115'
def main():
 rows=read(O/'placement-slices.json')['images'];test=read(B/'after-v4/manifest.json');comparison=read(B/'comparison.json');audit=read(B/'asset-audit.json')
 assert test['result']['passed']==1119 and test['result']['failed']==0
 assert comparison['classic_all_exact'] and len(comparison['classic_frames'])==18 and comparison['after'].endswith('after-v4')
 assert audit['crown_pixels_clipped_by_canvas']==0 and audit['exe_unchanged']
 assert sha(LIVE/'fallout-ce.exe')==test['executable_sha256'].lower()
 for row in rows:
  assert sha(LIVE/'data/art/hd/world-pilot'/row['file'])==row['before_sha256'],('Later edit',row['file'])
  assert sha(D/row['file'])==row['sha256']
 assert not (BACK/'state.json').exists(),'Existing installation; inspect before resuming'
 root=LIVE/'data/art/hd/world-pilot';names=[r['file'] for r in rows]+['manifest.json']
 protected={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.bmp','.log']}
 BACK.mkdir(parents=True,exist_ok=True);PKG.mkdir(parents=True,exist_ok=True);files=[]
 for name in names:
  shutil.copy2(root/name,BACK/name);files.append(dict(name=name,before_sha256=sha(root/name)))
 save(BACK/'state.json',dict(status='backed up',files=files))
 for row in rows:
  shutil.copy2(D/row['file'],root/row['file']);shutil.copy2(R/row['png'],PKG/Path(row['png']).name)
 for name in ['corner-render.png','fallout-wall-corner.blend','scene-registration.json','camera-calibration.json','placement-slices.json']:shutil.copy2(O/name,PKG/name)
 for name in ['scene.py','pack.py','README.txt']:shutil.copy2(W/name,PKG/name)
 m=read(root/'manifest.json');m['wall_geometry'].update(component='wall-crown-v4 + blender-corner-v1',alpha_preserved=False,report=str((B/'after-v4/manifest.json').relative_to(R)))
 patch=dict(component='blender-corner-v1',package=str(PKG.relative_to(R)),objects=sorted(SELECT),placement_images=11,base='wall-crown-v4',scene=str((PKG/'fallout-wall-corner.blend').relative_to(R)),alpha='New Blender silhouettes, quantized on original logical grid',executable_changed=False,assets=[dict(file=r['file'],sha256=r['sha256']) for r in rows])
 m['wall_geometry']['blender_corner_pilot']=patch;save(root/'manifest.json',m)
 for f in files:f['installed_sha256']=sha(root/f['name'])
 save(BACK/'state.json',dict(status='installed',files=files))
 changed={'data/art/hd/world-pilot/'+n for n in names};unchanged=0
 for rel,h in protected.items():
  if rel not in changed:assert sha(LIVE/rel)==h,('Unexpected change',rel);unchanged+=1
 for row in rows:assert sha(root/row['file'])==row['sha256']
 receipt=dict(status='installed and verified prototype',component='blender-corner-v1',updated_placement_sprites=11,objects=sorted(SELECT),scene=str((PKG/'fallout-wall-corner.blend').relative_to(R)),scene_sha256=sha(PKG/'fallout-wall-corner.blend'),render_sha256=sha(PKG/'corner-render.png'),authoring_script_sha256=sha(PKG/'scene.py'),assets=rows,checks=test['result'],audit=audit,comparison=comparison,exe_sha256=sha(LIVE/'fallout-ce.exe'),exe_changed=False,other_runtime_files_unchanged=unchanged,backup=str(BACK.relative_to(R)))
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='assets'})
 print('INSTALLED 11 Blender wall sprites; unchanged EXE and',unchanged,'other runtime files')
if __name__=='__main__':main()
