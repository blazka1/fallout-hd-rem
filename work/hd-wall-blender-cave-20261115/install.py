from prepare import *
PKG=R/'assets/hd/v13ent/blender-cave-v3';BACK=R/'build/backups/before-blender-cave-v3-20261115'
def main():
 record=read(O/'placement-slices.json');assert not record['preflight_only']
 rows=record['images'];test=read(B/'after-v1/manifest.json');comparison=read(B/'comparison.json');audit=read(B/'asset-audit.json')
 assert test['result']['passed']==1119 and test['result']['failed']==0
 assert comparison['classic_all_exact'] and len(comparison['classic_frames'])==18 and comparison['after'].endswith('after-v1')
 assert audit['render_pixels_outside_canvas']==0 and audit['exe_unchanged']
 region_audit=read(B/'render-region-audit.json')
 assert region_audit['all_camera_axes_calibrated'] and region_audit['mean_absolute_rgb']<3
 assert sha(LIVE/'fallout-ce.exe')==test['executable_sha256'].lower()
 for r in rows:
  assert sha(LIVE/'data/art/hd/world-pilot'/r['file'])==r['before_sha256'],('Later edit',r['file'])
  assert sha(D/r['file'])==r['sha256']
 assert not (BACK/'state.json').exists(),'Existing installation; inspect before resuming'
 root=LIVE/'data/art/hd/world-pilot';names=[r['file'] for r in rows]+['manifest.json']
 m=read(root/'manifest.json');assert 'assets' in m and 'wall_geometry' in m
 changed={'data/art/hd/world-pilot/'+n for n in names}
 for p in (LIVE/'data/art').rglob('*'):
  if p.is_file():
   rel=str(p.relative_to(LIVE)).replace('\\','/')
   if rel not in changed:assert sha(p)==sha(W/'runtime'/rel),('Refresh and retest newer shared art',rel)
 protected={str(p.relative_to(LIVE)).replace('\\','/'):sha(p) for p in LIVE.rglob('*') if p.is_file() and p.suffix.lower() not in ['.bmp','.log']}
 BACK.mkdir(parents=True);PKG.mkdir(parents=True,exist_ok=True);files=[]
 for name in names:
  shutil.copy2(root/name,BACK/name);files.append(dict(name=name,before_sha256=sha(root/name)))
 save(BACK/'state.json',dict(status='backed up',files=files))
 for r in rows:
  shutil.copy2(D/r['file'],root/r['file']);shutil.copy2(R/r['png'],PKG/Path(r['png']).name)
 for name in ['cave-render.png','fallout-cave-walls.blend','cap-material.blend','cap-periodic.png','cap-material-provenance.json','material-provenance.json','scene-registration.json','cave-render-camera.json','tile-layout.json','placement-slices.json','reference-rock-detail.png','reference-rock-periodic.png','geometry-contract.json']:
  shutil.copy2(O/name,PKG/name)
 for name in ['scene.py','geometry.py','pack.py','cap.py','cap-scene.py','stitch.py','README.txt']:shutil.copy2(W/name,PKG/name)
 shutil.copy2(B/'render-region-audit.json',PKG/'render-region-audit.json')
 byfile={r['file']:r for r in rows}
 for a in m['assets']:
  if a['filename'] in byfile:
   r=byfile[a['filename']];png=PKG/Path(r['png']).name
   a.update(runtime_file_sha256=r['sha256'],source_png=str(png),source_png_sha256=sha(png),appearance_component='blender-cave-v3',decoded_rgba_sha256=hashlib.sha256((D/r['file']).read_bytes()[20:]).hexdigest())
 m['wall_geometry'].update(component='blender-cave-v3',package=str(PKG.relative_to(R)),alpha_preserved=False,report=str((B/'after-v1/manifest.json').relative_to(R)),geometry_only=False,placement_images=417,cap_images=9,approved_door_preserved=True)
 if 'blender_corner_pilot' in m['wall_geometry']:m['wall_geometry']['blender_corner_pilot']['superseded_by']='blender-cave-v3'
 m['wall_geometry']['blender_cave']=dict(scene=str((PKG/'fallout-cave-walls.blend').relative_to(R)),material_base='blender-corner-v2',images=426,executable_changed=False)
 save(root/'manifest.json',m)
 for f in files:f['installed_sha256']=sha(root/f['name'])
 save(BACK/'state.json',dict(status='installed',files=files))
 changed={'data/art/hd/world-pilot/'+n for n in names};unchanged=0
 for rel,h in protected.items():
  if rel not in changed:assert sha(LIVE/rel)==h,('Unexpected change',rel);unchanged+=1
 for r in rows:assert sha(root/r['file'])==r['sha256']
 receipt=dict(status='installed and verified',component='blender-cave-v3',updated_placement_sprites=417,cap_images=9,door_object_252_preserved=True,scene=str((PKG/'fallout-cave-walls.blend').relative_to(R)),scene_sha256=sha(PKG/'fallout-cave-walls.blend'),assets=rows,checks=test['result'],audit=audit,comparison=comparison,exe_sha256=sha(LIVE/'fallout-ce.exe'),exe_changed=False,other_runtime_files_unchanged=unchanged,backup=str(BACK.relative_to(R)))
 receipt['render_region_audit']=region_audit
 save(PKG/'manifest.json',receipt);save(B/'integration.json',receipt);save(W/'task.json',{k:v for k,v in receipt.items() if k!='assets'})
 print('INSTALLED',len(rows),'images; unchanged EXE and',unchanged,'other runtime files')
if __name__=='__main__':main()
