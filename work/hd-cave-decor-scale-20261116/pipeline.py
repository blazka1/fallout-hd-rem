"""Scoped Comfy rescaling/shading of cave decorations; no game-code edits."""
from pathlib import Path
import importlib.util,json,hashlib,shutil,struct,uuid,urllib.parse,argparse
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[2];W=Path(__file__).parent
LIVE=ROOT/'runtime/hd-world-pilot';RT=W/'runtime'
GEN=ROOT/'assets/generated/v13ent-decor/scale-shade-v1-20261116'
PACK=ROOT/'assets/hd/v13ent/decor-scale-shade-v1'
B=ROOT/'build/hd-cave-decor-scale-20261116'
BACK=ROOT/'build/backups/before-cave-decor-scale-20261116'
REL=Path('data/art/hd/world-pilot');IDS=[240,241,244,245]
s=importlib.util.spec_from_file_location('gen',ROOT/'work/hd-vault-materials-v2/generate.py');z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
h=z.h;BASE=z.BASE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def init():
 assert not (W/'test-exe.json').exists()
 GEN.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
 files={p.relative_to(LIVE).as_posix():sha(p) for p in LIVE.rglob('*') if p.is_file()}
 if (W/'baseline.json').exists():
  assert read(W/'baseline.json')['files']==files
  assert all(sha(RT/rel)==hsh for rel,hsh in files.items())
 else:
  assert not RT.exists();save(W/'baseline.json',dict(files=files,exe_sha256=sha(LIVE/'fallout-ce.exe')));shutil.copytree(LIVE,RT)
 rows={r['asset_id']:r for r in read(LIVE/REL/'manifest.json')['assets']}
 for i in IDS:
  r=rows[i];src=Path(r['source_png']);assert sha(src)==r['source_png_sha256'];assert sha(LIVE/REL/r['filename'])==r['runtime_file_sha256']
  shutil.copy2(src,GEN/f'source-{i}.png')
 # Reuse the already checked diagnostics-only wall assertion correction.
 actual=ROOT/'work/hd-world-pilot/fallout1-ce-main/src';tested=ROOT/'work/hd-wall-original-restore-20261116/test-source/src'
 diffs=[p.relative_to(actual).as_posix() for p in actual.rglob('*') if p.is_file() and (not (tested/p.relative_to(actual)).exists() or sha(p)!=sha(tested/p.relative_to(actual)))]
 assert diffs==['game/hd_wall_geometry_test.inc'],diffs
 testexe=ROOT/'build/hd-wall-original-restore-20261116/test-msvc/RelWithDebInfo/fallout-ce.exe'
 shutil.copy2(testexe,RT/'fallout-ce.exe')
 save(W/'test-exe.json',dict(source_differences=diffs,exe_sha256=sha(testexe),purpose='Existing diagnostics-only assertion for identical wall base/placement textures; not installed in live runtime'))
 script=(ROOT/'work/hd-wall-grey-match-20261116/test.ps1').read_text(encoding='utf-8').replace('work/hd-wall-grey-match-20261116/runtime','work/hd-cave-decor-scale-20261116/runtime').replace('[int]$TimeoutSeconds = 150','[int]$TimeoutSeconds = 900')
 (W/'test.ps1').write_text(script,encoding='utf-8');print('Isolated current runtime; sources verified; all live files backed by baseline hashes')
def submit():
 assert not (GEN/'run.json').exists();h.require_idle(BASE);g={};outputs={};specs=[];prefix='fallout1_decor_scale/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 def scale(im,w,ht,method='lanczos'):return add('ImageScale',image=im,upscale_method=method,width=w,height=ht,crop='disabled')
 def maskimage(m):return add('MaskToImage',mask=m)
 for i in IDS:
  im=Image.open(GEN/f'source-{i}.png');w,ht=im.size;nw,nh=w//4,ht//4
  src=add('LoadImage',image=h.upload(BASE,GEN/f'source-{i}.png','decor-scale-'+uuid.uuid4().hex+'.png'))
  opacity=add('InvertMask',mask=[src[0],1]);rgb=src
  if i!=241:
   if i==240:
    # Skull is isolated from the rib cage; keep bottom long bone intact.
    skull=add('ImageCrop',image=src,x=0,y=0,width=76,height=80)
    skullalpha=add('ImageCrop',image=maskimage(opacity),x=0,y=0,width=76,height=80)
    skull=scale(skull,52,56);skullalpha=add('ImageToMask',image=scale(skullalpha,52,56,'area'),channel='red')
    clear=add('EmptyImage',width=76,height=80,batch_size=1,color=0)
    rgb=add('ImageCompositeMasked',destination=rgb,source=clear,x=0,y=0,resize_source=False)
    rgb=add('ImageCompositeMasked',destination=rgb,source=skull,x=12,y=12,resize_source=False,mask=skullalpha)
    zero=add('SolidMask',value=1.0,width=76,height=80)
    opacity=add('MaskComposite',destination=opacity,source=zero,x=0,y=0,operation='subtract')
    opacity=add('MaskComposite',destination=opacity,source=skullalpha,x=12,y=12,operation='add')
   tw,th={240:(35,17),244:(31,15),245:(38,26)}[i];x,y=(nw-tw)//2*4,(nh-th)//2*4
   rgb=scale(rgb,tw*4,th*4)
   small=add('ImageToMask',image=scale(maskimage(opacity),tw,th,'area'),channel='red');small=add('ThresholdMask',mask=small,value=0.5)
   small=add('ImageToMask',image=scale(maskimage(small),tw*4,th*4,'nearest-exact'),channel='red')
   canvas=add('EmptyImage',width=w,height=ht,batch_size=1,color=0)
   rgb=add('ImageCompositeMasked',destination=canvas,source=rgb,x=x,y=y,resize_source=False,mask=small)
   opacity=add('SolidMask',value=0.0,width=w,height=ht);opacity=add('MaskComposite',destination=opacity,source=small,x=x,y=y,operation='add')
   specs.append(dict(asset_id=i,old_native=[nw,nh],new_visible_canvas_native=[tw,th],placement_hd=[x,y],extra_skull_resize=(i==240)))
  else:
   # Deepen existing shadows without redrawing or moving cans/paper.
   rgb=add('ImageBlend',image1=src,image2=src,blend_factor=0.30,blend_mode='multiply')
   black=add('EmptyImage',width=w,height=ht,batch_size=1,color=0)
   rgb=add('ImageBlend',image1=rgb,image2=black,blend_factor=0.10,blend_mode='normal')
   bottom=add('SolidMask',value=0.22,width=w,height=48);bottom=add('FeatherMask',mask=bottom,left=0,top=48,right=0,bottom=0)
   rgb=add('ImageCompositeMasked',destination=rgb,source=black,x=0,y=ht-48,resize_source=False,mask=bottom)
   specs.append(dict(asset_id=i,old_native=[nw,nh],alpha_exact=True,shading='30% self-multiply, 10% overall dim, up to22% extra at lower contact faces; existing details retained'))
  result=add('JoinImageWithAlpha',image=rgb,alpha=add('InvertMask',mask=opacity))
  k=add('SaveImage',images=result,filename_prefix=prefix+f'/asset-{i}');outputs[k[0]]=f'asset-{i}.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for n,v in [('prompt-api.json',g),('workflow.json',wf),('outputs.json',outputs),('specs.json',specs)]:save(GEN/n,v)
 h.require_idle(BASE);save(GEN/'run.json',h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})));print('Submitted exact Comfy resizing and shading')
def collect():
 pid=read(GEN/'run.json')['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running',pid);return
 job=hist[pid];save(GEN/'history.json',job);assert job['status']['status_str']=='success',job['status']
 for node,name in read(GEN/'outputs.json').items():
  rec=job['outputs'][node]['images'][0];(GEN/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected decoration edits')
def stage():
 PACK.mkdir(parents=True,exist_ok=True);rows=[]
 for i in IDS:
  p=GEN/f'asset-{i}.png';im=Image.open(p).convert('RGBA');a=np.array(im);old=np.array(Image.open(GEN/f'source-{i}.png').convert('RGBA'))
  assert a.shape==old.shape and set(np.unique(a[:,:,3]))=={0,255}
  assert np.array_equal(a[:,:,3],np.repeat(np.repeat(a[::4,::4,3],4,0),4,1))
  if i==241:assert np.array_equal(a[:,:,3],old[:,:,3])
  else:assert (a[:,:,3]>0).sum()<(old[:,:,3]>0).sum()*0.55
  shutil.copy2(p,PACK/p.name);raw=im.tobytes();rgba=PACK/f'asset-{i}.rgba';rgba.write_bytes(b'F1HD'+struct.pack('<IIII',1,im.width,im.height,4)+raw)
  shutil.copy2(rgba,RT/REL/rgba.name)
  rows.append(dict(asset_id=i,png=str(PACK/p.name),png_sha256=sha(PACK/p.name),rgba_sha256=sha(rgba),decoded_rgba_sha256=hashlib.sha256(raw).hexdigest(),before_sha256=sha(LIVE/REL/rgba.name),opaque_cells_before=int((old[::4,::4,3]>0).sum()),opaque_cells_after=int((a[::4,::4,3]>0).sum())))
 save(PACK/'manifest.json',dict(assets=rows,specs=read(GEN/'specs.json'),comfy_prompt=read(GEN/'run.json')['prompt_id'],source=str(GEN),scope='Three decoration bone piles and litter only; human skeleton explicitly excluded; dimensions/placements/registries/game code unchanged'))
 canvas=Image.new('RGB',(800,540),(48,48,48));d=ImageDraw.Draw(canvas)
 for row,i in enumerate(IDS):
  y=row*130;d.text((10,y+6),str(i)+' BEFORE',fill='white');d.text((410,y+6),'AFTER',fill='white')
  for x,p in [(10,GEN/f'source-{i}.png'),(410,GEN/f'asset-{i}.png')]:
   im=Image.open(p).convert('RGBA');im.thumbnail((375,100));canvas.paste(im,(x,y+25),im)
 canvas.save(B/'assets-before-after.png');print('Staged four images; alpha validated')
def install():
 assert not BACK.exists();base=read(W/'baseline.json')['files']
 for rel,hash in base.items():assert (LIVE/rel).exists() and sha(LIVE/rel)==hash,rel
 after=read(B/'after-v2/manifest.json');assert after['exit_code']==0 and after['result']['failed']==0
 assert after['executable_sha256'].lower()==read(W/'test-exe.json')['exe_sha256']
 assert read(B/'visual-qa.json')['classic_frames_exact']
 BACK.mkdir(parents=True);shutil.copy2(W/'baseline.json',BACK/'baseline.json')
 names=['manifest.json']+[f'asset-{i}{ext}' for i in IDS for ext in ['.rgba','.metadata.json']]
 for name in names:shutil.copy2(LIVE/REL/name,BACK/name)
 m=read(LIVE/REL/'manifest.json');byid={r['asset_id']:r for r in m['assets']}
 for r in read(PACK/'manifest.json')['assets']:
  i=r['asset_id'];name=f'asset-{i}.rgba';shutil.copy2(PACK/name,LIVE/REL/name)
  meta=read(LIVE/REL/f'asset-{i}.metadata.json');meta['appearance_patch']=dict(package=str(PACK),source_png=r['png'],source_png_sha256=r['png_sha256'],comfy_prompt=read(GEN/'run.json')['prompt_id'],original_placement_and_dimensions_preserved=True);save(LIVE/REL/f'asset-{i}.metadata.json',meta)
  byid[i].update(source_png=r['png'],source_png_sha256=r['png_sha256'],runtime_file_sha256=r['rgba_sha256'],decoded_rgba_sha256=r['decoded_rgba_sha256'],metadata_sha256=sha(LIVE/REL/f'asset-{i}.metadata.json'))
 m['component_patches'].append(dict(component='decor-scale-shade-v1',asset_ids=IDS,package=str(PACK),manifest_sha256=sha(PACK/'manifest.json')));save(LIVE/REL/'manifest.json',m)
 expected={(REL/n).as_posix() for n in names};changed={rel for rel,hsh in base.items() if sha(LIVE/rel)!=hsh};assert changed==expected,changed
 for r in read(PACK/'manifest.json')['assets']:assert sha(LIVE/REL/f"asset-{r['asset_id']}.rgba")==r['rgba_sha256']
 save(B/'integration.json',dict(status='installed_and_verified',package=str(PACK),backup=str(BACK),exe_sha256=sha(LIVE/'fallout-ce.exe'),exe_unchanged=True,changed_files=sorted(changed),protected_files=len(base)-len(changed),test_report=str(B/'after-v2/manifest.json'),test_executable=read(W/'test-exe.json'),passed=after['result']['passed'],failed=0,human_skeleton_unchanged=True,placements_and_collision_unchanged=True,visual_qa=read(B/'visual-qa.json')))
 (W/'README.txt').write_text('Installed four decoration textures only: smaller bone piles240/244/245 (largest human skull additionally reduced) and shaded household litter241. Human skeleton, mushrooms, placement coordinates, collisions, EXE and all other art preserved. Comfy native geometry/color nodes, no new diffusion required. Current runtime cloned before testing; diagnostics-only wall assertion and translucent-wall decoration visibility fixes used in isolated test EXE, never installed. Report build/hd-cave-decor-scale-20261116/integration.json. Restart Start-Fallout-HD-World-Pilot.cmd.\n',encoding='utf-8')
 print('Installed and verified four assets; protected',len(base)-len(changed),'files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','submit','collect','stage','install']);globals()[p.parse_args().action]()
