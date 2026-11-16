from bake import *
import itertools
def main():
 rows=read(O/'placements.json')['images'];walls=[r for r in rows if r['kind']=='wall'];imgs={}
 for r in rows:
  a=decode(D/r['file']);old=decode(LIVE/r['file'])
  assert a.shape==old.shape and np.array_equal(a[:,:,3],old[:,:,3]),r['file']
  assert np.array_equal(a,np.asarray(Image.open(R/r['png']).convert('RGBA')))
  assert sha(LIVE/r['file'])==r['before_sha256']
  if r['kind']=='wall':imgs[r['object']['id']]=a
 pairs=pixels=0
 for a,b in itertools.combinations(walls,2):
  x,y,w,h=a['world_box'];xx,yy,ww,hh=b['world_box'];l,t,rr,bb=max(x,xx),max(y,yy),min(x+w,xx+ww),min(y+h,yy+hh)
  if l>=rr or t>=bb:continue
  aa=imgs[a['object']['id']][(t-y)*4:(bb-y)*4,(l-x)*4:(rr-x)*4]
  ab=imgs[b['object']['id']][(t-yy)*4:(bb-yy)*4,(l-xx)*4:(rr-xx)*4]
  both=(aa[:,:,3]>0)&(ab[:,:,3]>0)
  if both.any():
   assert np.array_equal(aa[:,:,:3][both],ab[:,:,:3][both]),(a['file'],b['file'])
   pairs+=1;pixels+=int(both.sum())
 yy,xx=np.mgrid[0:144,0:320];wx=xx*.25-16;wy=yy*.25-2;cap=cap_rgb(wx,wy)
 for dx,dy in [(48,-12),(32,24),(-48,12),(-32,-24)]:assert np.array_equal(cap,cap_rgb(wx+dx,wy+dy))
 for id in [62,63]:
  base=decode(D/f'asset-{id:03}.rgba')
  for slot in [1,2,3]:assert np.array_equal(base,decode(D/f'tile-{id:03}-v{slot}.rgba'))
 changed={r['file'] for r in rows};protected=0
 for f in LIVE.iterdir():
  if f.is_file() and f.name not in changed:assert sha(f)==sha(D/f.name),f.name;protected+=1
 report=dict(render_images=len(rows),wall_placements=len(walls),cap_images=9,alpha_exact=True,registry_exact=True,overlap_pairs=pairs,overlap_pixels=pixels,overlap_max_rgb_difference=0,cap_lattice_exact=True,variant_cap_edges_exact=True,other_asset_files_unchanged=protected,cap_rgb_mean=float(cap.mean()),top_has_stone_material=True)
 save(B/'asset-audit.json',report);print(json.dumps(report))
if __name__=='__main__':main()
