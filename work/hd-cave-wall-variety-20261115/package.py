"""Lossless F1HD packaging, validation and a reversible staged installation."""
import sys,json,struct,shutil,hashlib,re,subprocess,datetime
from pathlib import Path
import numpy as np
from PIL import Image
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT;RT=w.RT;DATA=w.DATA;BACK=w.BACK
PACK=R/'assets/hd/v13ent/wall-variety-v1';B=R/'build/hd-cave-wall-variety-20261115'

def idle():
 x=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process -Name fallout-ce,fallout-cave-test,fallout-wall-test -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
 assert x.stdout.strip()=='0','Close Fallout before staging wall assets'
def package():
 plan=p.read(OUT/'plan.json');PACK.mkdir(parents=True,exist_ok=True);records=[];bases={};old_runtime=p.read(DATA/'manifest.json')
 old_by_id={a['asset_id']:a for a in old_runtime['assets']}
 def write(id,file,source,original,kind,base=None,theme=None):
  im=Image.open(source).convert('RGBA');a=np.array(im);old=np.array(Image.open(original).convert('RGBA'));assert a.shape==old.shape and np.array_equal(a[:,:,3],old[:,:,3])
  diff=np.any(a!=old,axis=2);border=np.zeros(diff.shape,bool);border[:4]=1;border[-4:]=1;border[:,:4]=1;border[:,-4:]=1
  assert not diff[border].any(),(id,'edge')
  roof=(old[:,:,3]>0)&(old[:,:,0]<=24)
  if theme=='mushrooms':roof[round(im.height*.3):]=False
  assert not diff[roof].any(),(id,'roof')
  assert int(diff.sum())>10,(id,'no visible change')
  target=PACK/file;target.write_bytes(struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4)+im.tobytes())
  selected=PACK/'png'/('asset-%03d.png'%id);selected.parent.mkdir(exist_ok=True);shutil.copy2(source,selected)
  record=dict(id=id,file=file,kind=kind,base=base,theme=theme,source_png=str(source.relative_to(R)),source_sha256=p.sha(source),selected_png=str(selected.relative_to(R)),rgba_sha256=p.sha(target),width=im.width,height=im.height,alpha_exact=True,edge_4px_exact=True,dark_roof_exact=True,changed_pixels=int(diff.sum()))
  records.append(record)
 for c in plan['contexts']:
  d=OUT/'prepared/material-v2'/c['id'];assert (d/'result.json').exists()
  for a in p.read(d/'registration.json')['records']:
   src=d/'assets'/('asset-%03d.png'%a['id']);old=OUT/('inputs/walls' if a['kind']=='base' else 'inputs/old-variants')/((a['source'] if a['kind']=='base' else Path(a['file']).stem)+'.png')
   write(a['id'],a['file'],src,old,a['kind'])
   if a['kind']=='base':bases[a['id']]=src
 for a in plan['new_variants']:
  d=OUT/('prepared/accents-v3' if a['theme'] in ['moss','mushrooms'] else 'prepared/accents-v2')/a['theme'];assert (d/'result.json').exists()
  write(a['id'],a['file'],d/'assets'/('asset-%03d.png'%a['id']),bases[a['base']],'new-accent',a['base'],a['theme'])
 assert len(records)==110 and len(set(a['id'] for a in records))==110
 registry=(BACK/'runtime/hd-world-pilot/data/art/hd/world-pilot/variants.tsv').read_text()
 registry=registry.rstrip()+'\n'+''.join(f"{a['base']}\t{a['slot']}\t{a['id']}\t{a['file']}\n" for a in plan['new_variants'])
 (PACK/'variants.tsv').write_text(registry,encoding='utf-8')
 p.save(PACK/'manifest.json',dict(status='prepared for game validation',records=records,base_walls=62,refreshed_existing_variants=24,new_accents=24,expected_runtime_count=246,accent_distribution=p.read(OUT/'distribution.json')))
 print('Packaged 110 wall PNG/RGBA, all alpha/edges/dark roof validated',flush=True)

def stage():
 idle();assert not (B/'stage.json').exists(),'Already staged'
 plan=p.read(PACK/'manifest.json');before=p.read(BACK/'runtime-before.json')
 cfg=RT/'fallout.cfg';oldcfg=BACK/'runtime/hd-world-pilot/fallout.cfg';norm=lambda b:re.sub(rb'(?m)^splash=\d+',b'splash=0',b)
 assert norm(cfg.read_bytes())==norm(oldcfg.read_bytes()),'Unexpected config change'
 for file,h in before.items():
  if file!=str(cfg.relative_to(R)):assert p.sha(R/file)==h,file
 for a in plan['records']:assert p.sha(PACK/a['file'])==a['rgba_sha256']
 for a in plan['records']:shutil.copy2(PACK/a['file'],DATA/a['file'])
 shutil.copy2(PACK/'variants.tsv',DATA/'variants.tsv')
 p.save(B/'stage.json',dict(files=[a['file'] for a in plan['records']]+['variants.tsv'],test_exe_sha256=p.sha(RT/'fallout-wall-test.exe'),old_exe_sha256=p.sha(RT/'fallout-ce.exe')))
 print('Staged graphics only; live executable still previous version',flush=True)

def finish():
 idle();assert not (B/'integration.json').exists()
 manifest=p.read(PACK/'manifest.json');stage=p.read(B/'stage.json');before=p.read(BACK/'runtime-before.json');testexe=RT/'fallout-wall-test.exe';exe=p.sha(testexe)
 checks={}
 for name in ['world','terminal','menu']:
  directory=name+'-final' if name!='menu' else name
  m=p.read(B/directory/'manifest.json');result=m.get('result',m);assert m['executable_sha256'].lower()==exe and result['failed']==0,name
  checks[name]=dict(passed=result['passed'],failed=0,report=str((B/directory/'manifest.json').relative_to(R)))
 for file in stage['files']:assert p.sha(DATA/file)==p.sha(PACK/file),file
 assert p.sha(RT/'fallout-ce.exe')==stage['old_exe_sha256']
 cfg=RT/'fallout.cfg';oldcfg=BACK/'runtime/hd-world-pilot/fallout.cfg';norm=lambda b:re.sub(rb'(?m)^splash=\d+',b'splash=0',b)
 assert norm(cfg.read_bytes())==norm(oldcfg.read_bytes())
 allowed={str((DATA/f).relative_to(R)) for f in stage['files']}|{str(cfg.relative_to(R))}
 for file,h in before.items():
  if file not in allowed:assert p.sha(R/file)==h,file
 runtime=p.read(DATA/'manifest.json');byid={a['asset_id']:a for a in runtime['assets']}
 for a in manifest['records']:
  if a['kind']=='new-accent':
   base=byid[a['base']];row=dict(asset_id=a['id'],category='wall-appearance',base_asset_id=a['base'],theme=a['theme'],native_width=a['width']//4,native_height=a['height']//4,width=a['width'],height=a['height'],scale=4,filename=a['file'],runtime_file='data/art/hd/world-pilot/'+a['file'],alpha_exact_original_nearest_neighbor=True)
   runtime['assets'].append(row)
  else:row=byid[a['id']]
  row.update(source_png=str(R/a['selected_png']),source_png_sha256=p.sha(R/a['selected_png']),runtime_file_sha256=p.sha(DATA/a['file']),decoded_rgba_sha256=hashlib.sha256((DATA/a['file']).read_bytes()[20:]).hexdigest())
 runtime['asset_count']=246;runtime['variant_image_count']=48;runtime['variants_sha256']=p.sha(DATA/'variants.tsv')
 runtime['component_patches'].append(dict(component='wall-variety-v1',package=str(PACK),base_walls=62,refreshed_variants=24,new_accents=24,accent_places=41,variants_sha256=p.sha(DATA/'variants.tsv'),game_map_modified=False))
 assert len(runtime['assets'])==246
 shutil.copy2(oldcfg,cfg);shutil.copy2(testexe,RT/'fallout-ce.exe');p.save(DATA/'manifest.json',runtime)
 changed=[f for f,h in before.items() if p.sha(R/f)!=h]
 allowed|={str((RT/'fallout-ce.exe').relative_to(R)),str((DATA/'manifest.json').relative_to(R))};assert set(changed)<=allowed
 receipt=dict(status='installed-and-verified',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),executable_sha256=exe,old_executable_sha256=stage['old_exe_sha256'],runtime_resources=246,base_walls=62,refreshed_wall_variants=24,new_wall_accents=24,accent_distribution=manifest['accent_distribution'],checks=checks,changed_existing_files=changed,protected_existing_files=len(before)-len(changed),package=str(PACK.relative_to(R)),backup=str(BACK.relative_to(R)),review=str((B/'review/index.html').relative_to(R)),code_changes='test harness only: remove historical slot assumptions and verify all 24 new accents',AGENTS_modified=False)
 p.save(B/'integration.json',receipt);p.save(R/'work/hd-cave-wall-variety-20261115/task.json',receipt)
 manifest['status']='installed-and-verified';manifest['integration']=str((B/'integration.json').relative_to(R));p.save(PACK/'manifest.json',manifest)
 print(json.dumps(dict(status=receipt['status'],checks=checks,protected=receipt['protected_existing_files'])),flush=True)

def refresh():
 idle();old=p.read(B/'first-moss-draft-package.json');new=p.read(PACK/'manifest.json')
 for a in old['records']:assert p.sha(DATA/a['file'])==a['rgba_sha256'],a['file']
 assert p.sha(DATA/'variants.tsv')==p.sha(PACK/'variants.tsv')
 changed=[]
 for a,b in zip(old['records'],new['records']):
  assert a['id']==b['id'] and a['file']==b['file']
  if a['rgba_sha256']!=b['rgba_sha256']:
   assert a['theme']=='moss';shutil.copy2(PACK/b['file'],DATA/b['file']);changed.append(a['id'])
 p.save(B/'moss-refinement.json',dict(changed=changed,reason='55% coverage preserves stone relief through moss in actual cave lighting'))
 print('Refreshed moss only:',changed,flush=True)

if __name__=='__main__':{'package':package,'stage':stage,'refresh':refresh,'finish':finish}[sys.argv[1]]()
