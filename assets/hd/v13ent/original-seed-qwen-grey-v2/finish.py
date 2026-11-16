from pipeline import *
from scipy import ndimage as nd

def fit_caps():
 plan=read(O/'plan.json');old=np.array(Image.open(O/'inputs/caps/current.png').convert('RGBA'));mask=old[:,:,3]>0
 base=np.array(Image.open(O/'colour/caps-current/grey.png').convert('RGB'));raw=np.array(Image.open(O/'qwen/caps/raw.png').convert('RGB'));assert raw.shape==base.shape
 luma=raw@np.array([.2126,.7152,.0722]);gain=float(np.mean(base[:,:,0][mask])/max(1,np.mean(luma[mask])));assert .25<gain<2
 d=O/'colour/caps-qwen'
 if not (d/'result.json').exists():
  g,outputs=grey_graph(O/'qwen/caps/raw.png',gain=gain,offset=0);h.execute(d,g,outputs)
 guard=np.zeros(mask.shape,np.uint8)
 for s in plan['caps']['slots']:
  x,y,w,hh=s['x']*4,s['y']*4,s['width']*4,s['height']*4
  m=mask[y:y+hh,x:x+w];dist=nd.distance_transform_edt(np.pad(m,1))[1:-1,1:-1]
  guard[y:y+hh,x:x+w]=np.rint(np.clip((dist-8)/16,0,1)*255).astype(np.uint8)
 Image.fromarray(guard).convert('RGB').save(O/'inputs/caps/interior-mask.png')
 d=O/'caps-fit'
 if not (d/'result.json').exists():
  g={'1':node('LoadImage',image=h.upload(O/'colour/caps-current/grey.png')),'2':node('LoadImage',image=h.upload(O/'colour/caps-qwen/grey.png')),'3':node('LoadImage',image=h.upload(O/'inputs/caps/interior-mask.png')),
  '4':node('ImageToMask',image=['3',0],channel='red'),
  '5':node('ImageBlend',image1=['1',0],image2=['2',0],blend_factor=.25,blend_mode='normal'),
  '6':node('ImageCompositeMasked',destination=['1',0],source=['5',0],x=0,y=0,resize_source=False,mask=['4',0]),
  '7':node('SaveImage',images=['6',0],filename_prefix='fallout1_grey_match/'+uuid.uuid4().hex+'/cap-fit')}
  h.execute(d,g,{'7':'caps-fitted.png'})
 save(O/'caps-fit/selection.json',dict(qwen_neutral_gain=gain,qwen_interior_mix=.25,edge_guard_hd=8,fade_hd=16,geometry='current alpha and UV registration exact; boundary colors use shared wall transform',source_prompt_id=read(O/'qwen/caps/run.json')['prompt_id']))
 print('CAP FIT COMPLETE',flush=True)

def stage():
 plan=read(O/'plan.json');masters={};audit=[]
 for panel in plan['wall_panels']:
  sheet=np.array(Image.open(O/'colour'/panel['id']/'grey.png').convert('RGB'))
  for s in panel['slots']:
   before=np.array(Image.open(R/s['png']).convert('RGBA'));a=before.copy();x,y,w,hh=s['x'],s['y'],s['width'],s['height']
   a[:hh,:w,:3]=sheet[y:y+hh,x:x+w];a[a[:,:,3]==0,:3]=0
   masters[s['source']]=a;mask=before[:,:,3]>0
   expected=np.clip((before[:,:,:3]@np.array([.2126,.7152,.0722]))*1.18+4,0,255)
   error=float(np.max(np.abs(a[:,:,0].astype(float)-expected)[mask]));assert error<1.01
   assert np.max(np.ptp(a[:,:,:3][mask].astype(int),axis=1))==0
   audit.append(dict(source=s['source'],old_mean_rgb=before[:,:,:3][mask].mean(0).tolist(),new_mean_rgb=a[:,:,:3][mask].mean(0).tolist(),max_pointwise_curve_error=error))
 fitted=np.array(Image.open(O/'caps-fit/caps-fitted.png').convert('RGB'));base=np.array(Image.open(O/'colour/caps-current/grey.png').convert('RGB'));old=np.array(Image.open(O/'inputs/caps/current.png').convert('RGBA'));guard=np.array(Image.open(O/'inputs/caps/interior-mask.png').convert('L'))
 fitted[guard==0]=base[guard==0]
 for s in plan['caps']['slots']:
  x,y,w,hh=s['x']*4,s['y']*4,s['width']*4,s['height']*4;a=old[y:y+hh,x:x+w].copy();a[:,:,:3]=fitted[y:y+hh,x:x+w];a[a[:,:,3]==0,:3]=0
  assert np.max(np.ptp(a[:,:,:3].astype(int),axis=2))==0
  masters[s['source']]=a
 rows=[];baseline=read(W/'baseline.json');targets=read(O/'targets.json')
 for name,t in targets.items():
  a=masters['door-clearance' if t['kind']=='door' else t['source']];before=decode(LIVE/'data/art/hd/world-pilot'/name)
  assert a.shape==before.shape and np.array_equal(a[:,:,3],before[:,:,3]),name
  pack(D/name,a);png=O/'runtime-png'/name.replace('.rgba','.png');png.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(a).save(png)
  rows.append(dict(file=name,source=t['source'],kind=t['kind'],before_sha256=baseline['files']['data/art/hd/world-pilot/'+name],sha256=sha(D/name),png=str(png.relative_to(R))))
 changed={'data/art/hd/world-pilot/'+a['file'] for a in rows};protected=0
 for rel,hsh in baseline['files'].items():
  if rel.startswith('data/art/') and rel not in changed:
   assert sha(W/'runtime'/rel)==hsh,rel;protected+=1
 assert sha(W/'runtime/fallout-ce.exe')==baseline['exe_sha256']
 for s in read(O/'reference-measurements.json'):assert sha(D/s['file'])==s['sha256']
 save(O/'images.json',rows);save(B/'asset-audit.json',dict(images=len(rows),alpha_exact_before_all=True,dimensions_exact_before_all=True,registration_files_unchanged=True,wall_curve_exact=True,all_neutral_grey=True,wall_samples=audit,cap_edges_use_shared_curve=True,cap_selection=read(O/'caps-fit/selection.json'),reference_rocks_unchanged=True,protected_art_files=protected,exe_unchanged=True))
 print('STAGED',len(rows),'images; all alpha and dimensions identical; rock references untouched',flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage');args=a.parse_args();{'fit':fit_caps,'stage':stage}[args.stage]()
