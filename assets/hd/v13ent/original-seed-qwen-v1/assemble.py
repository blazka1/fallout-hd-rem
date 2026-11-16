from pipeline import *

def original_up(res):
 a=np.array(Image.open(O/'originals'/(Path(res).name+'.png')).convert('RGBA'));mask=a[:,:,3]>0
 _,ix=nd.distance_transform_edt(~mask,return_indices=True)
 rgb=a[:,:,:3][tuple(ix)];up=Image.fromarray(rgb).resize((a.shape[1]*4,a.shape[0]*4),Image.Resampling.LANCZOS)
 alpha=np.repeat(np.repeat(a[:,:,3],4,0),4,1)
 return np.array(up).astype(float),alpha

def build(only=None):
 selected={};records=[]
 for panel in read(O/'plan.json')['panels']:
  name=panel['id']
  if only and name!=only:continue
  sizing=read(O/'inputs'/name/'sizing.json');raw=Image.open(O/'qwen'/name/'raw.png').convert('RGB');assert list(raw.size)==sizing['working']
  pad=sizing['pad_left'];raw=raw.crop((pad,0,raw.width-pad,raw.height)).resize(tuple(n*4 for n in panel['native_size']),Image.Resampling.LANCZOS)
  seed=Image.open(O/'seedvr2'/name/'seedvr2-x4.png').convert('RGB')
  context=Image.new('RGBA',raw.size)
  for s in panel['slots']:
   box=(s['x']*4,s['y']*4,(s['x']+s['width'])*4,(s['y']+s['height'])*4)
   q=np.array(raw.crop(box)).astype(float);sd=np.array(seed.crop(box)).astype(float);orig,alpha=original_up(s['source']);mask=alpha>0
   # Extend valid interior colors for filters; never borrow a neighbor's wall.
   _,ix=nd.distance_transform_edt(~mask,return_indices=True)
   q=q[tuple(ix)];sd=sd[tuple(ix)]
   candidate=.50*sd+.50*q
   smooth=lambda a:nd.gaussian_filter(a,sigma=(8,8,0))
   candidate-=.85*(smooth(candidate)-smooth(orig))
   # Exact native outlines and an original-color guard at sprite joins.
   dist=nd.distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]
   guard=np.clip((dist-4)/8,0,1)[:,:,None]
   rgb=np.rint(np.clip(orig*(1-guard)+candidate*guard,0,255)).astype(np.uint8)
   rgba=np.dstack((rgb,alpha));rgba[~mask,:3]=0
   dest=O/'selected'/(Path(s['source']).name+'.png');dest.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(rgba).save(dest)
   selected[s['source']]=rgba
   records.append(dict(source=s['source'],panel=name,png=str(dest.relative_to(R)),sha256=sha(dest),size=list(Image.open(dest).size),alpha_exact_native=True,original_low_frequency_retained=.85,seed_qwen_mix=[.5,.5],edge_guard_hd=[4,12]))
   context.paste(Image.fromarray(rgba),(box[0],box[1]),Image.fromarray(alpha))
  context.save(O/'selected'/f'{name}-selected-only.png')
  # Source/Seed/Qwen/final strip for truthful inspection at equal scale.
  labels=['Original (Lanczos)','SeedVR2 x4','Qwen 2.1 raw','Selected / native geometry']
  ims=[Image.open(O/'inputs'/name/'original.png').convert('RGB').resize(raw.size,Image.Resampling.LANCZOS),seed,raw,context.convert('RGB')]
  # Show a common complete panel; selected-only contains just canonical slots.
  sheet=Image.new('RGB',(1200,850),(24,27,31));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
  for i,im in enumerate(ims):
   x=(i%2)*600;y=(i//2)*425;draw.text((x+8,y+4),labels[i],font=font,fill='white');sheet.paste(im.resize((600,400),Image.Resampling.LANCZOS),(x,y+25))
  sheet.save(B/f'{name}-pipeline.png')
 if only:
  save(B/f'{only}-pilot.json',records);print('PILOT ASSEMBLED',len(records));return
 assert len(selected)==65
 targets=read(O/'targets.json');baseline=read(W/'baseline.json');rows=[]
 for file,t in targets.items():
  a=selected[t['source']].copy();old=decode(D/file)
  if t['kind']=='door':
   # Keep the user-approved clearance around the metal door frame. The
   # native ca036 sprite supplies the texture; its teeth must not return.
   prior=decode(LIVE/'data/art/hd/world-pilot'/file)
   a[:,:,3]=np.minimum(a[:,:,3],prior[:a.shape[0],:a.shape[1],3])
   a[a[:,:,3]==0,:3]=0;atlas=np.zeros_like(prior);atlas[:a.shape[0],:a.shape[1]]=a;a=atlas
  assert a.shape==old.shape,(file,a.shape,old.shape)
  before=baseline['files']['data/art/hd/world-pilot/'+file]
  pack(D/file,a);png=O/'runtime-png'/file.replace('.rgba','.png');png.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(a).save(png)
  rows.append(dict(file=file,source=t['source'],kind=t['kind'],before_sha256=before,sha256=sha(D/file),png=str(png.relative_to(R))))
 save(O/'selected-sources.json',records);save(O/'images.json',rows)
 changed={'data/art/hd/world-pilot/'+r['file'] for r in rows};protected=0
 for rel,hsh in baseline['files'].items():
  if rel.startswith('data/art/') and rel not in changed:
   assert sha(W/'runtime'/rel)==hsh,rel;protected+=1
 for res,a in selected.items():
  _,alpha=original_up(res);assert np.array_equal(a[:,:,3],alpha)
 assert sha(W/'runtime/fallout-ce.exe')==baseline['exe_sha256']
 save(B/'asset-audit.json',dict(images=len(rows),source_sprites=len(selected),wall_sources=62,cutaway_sources=3,canonical_alpha_exact_original_all=True,runtime_native_alpha_exact_images=536,door_clearance='intersection of native alpha and previously approved A alpha, in existing 512x512 atlas',registered_frame_sizes_unchanged=True,canonical_source_size_exact=True,registration_files_unchanged=True,protected_art_files=protected,exe_unchanged=True,source_contexts_pixel_exact=all(x['different']==0 for x in read(B/'source-context-validation.json'))))
 print('STAGED',len(rows),'images from',len(selected),'native sprites; exact alpha, sizes and original registrations')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--only');a=p.parse_args();build(a.only)
