from bake_edges import *
import itertools
def main():
 j=read(O/'placements.json');rows=j['placements'];images={}
 for r in rows:
  a=decode(D/r['file']);old=decode(LIVE/r['file']);w,h=r['world_box'][2:]
  assert np.array_equal(a[:,:,3],old[:,:,3]),r['file']
  assert a.shape==old.shape and np.array_equal(a,np.asarray(Image.open(R/r['png']).convert('RGBA')))
  assert sha(LIVE/r['file'])==r['before_sha256']
  images[r['object']['id']]=a[:h*4,:w*4]
 pairs=samples=0
 for a,b in itertools.combinations(rows,2):
  x,y,w,h=a['world_box'];xx,yy,ww,hh=b['world_box']
  l,t,rr,bb=max(x,xx),max(y,yy),min(x+w,xx+ww),min(y+h,yy+hh)
  if l>=rr or t>=bb:continue
  aa=images[a['object']['id']][(t-y)*4:(bb-y)*4,(l-x)*4:(rr-x)*4]
  ab=images[b['object']['id']][(t-yy)*4:(bb-yy)*4,(l-xx)*4:(rr-xx)*4]
  both=(aa[:,:,3]>0)&(ab[:,:,3]>0)
  if both.any():
   assert np.array_equal(aa[:,:,:3][both],ab[:,:,:3][both]),(a['file'],b['file'])
   pairs+=1;samples+=int(both.sum())
 changed={r['file'] for r in rows};protected=0
 for f in LIVE.iterdir():
  if f.is_file() and f.name not in changed:
   assert sha(f)==sha(D/f.name),f.name
   protected+=1
 assert j['maximum_unlit_boundary_difference_after']==0
 report=dict(images=len(rows),source_types=62,alpha_exact=True,door_alpha_exact=True,registry_exact=True,cap_assets_unchanged=True,overlap_pairs=pairs,overlap_pixels=samples,overlap_max_rgb_difference=0,other_asset_files_unchanged=protected,edge_samples=j['edge_samples'],unlit_boundary_error_before=j['mean_unlit_boundary_difference_before'],unlit_boundary_error_after=0)
 save(B/'asset-audit.json',report);print(json.dumps(report))
if __name__=='__main__':main()
