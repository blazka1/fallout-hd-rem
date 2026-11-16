from pack import *
import sys
def main():
 rows=read(O/'placement-slices.json')['images'];baseline=read(W/'baseline.json');changed={'data/art/hd/world-pilot/'+r['file'] for r in rows}
 assert len(rows)==11 and {r['object_id'] for r in rows}==SELECT
 unchanged=0
 for rel,h in baseline['files'].items():
  if rel.startswith('data/art/') or rel=='fallout-ce.exe':
   if rel not in changed:assert sha(W/'runtime'/rel)==h,rel;unchanged+=1
 for r in rows:
  a=decode(D/r['file']);h,w=a.shape[:2];alpha=a[:,:,3];assert np.isin(alpha,[0,255]).all()
  assert np.array_equal(alpha,np.repeat(np.repeat(alpha[::4,::4],4,0),4,1))
  assert sha(D/r['file'])==r['sha256']
 reg=read(O/'scene-registration.json');box=reg['box'];render=np.asarray(Image.open(O/'corner-render.png'));rh,rw=render.shape[:2]
 coverage=np.zeros((rh,rw),bool)
 for r in rows:
  x,y,w,h=r['world_box'];xa=max(0,(x-box[0])*4);ya=max(0,(y-box[1])*4);xb=min(rw,(x+w-box[0])*4);yb=min(rh,(y+h-box[1])*4)
  if xb>xa and yb>ya:coverage[ya:yb,xa:xb]=True
 yy,xx=np.mgrid[:rh,:rw];wx=box[0]+xx/4
 interior=(wx>=4220)&(wx<=4405);visible=render[:,:,3]>=128
 # New crown must fit above the side face without being cut into canvas stairs.
 top=np.zeros_like(visible)
 for x in range(rw):
  ys=np.flatnonzero(visible[:,x])
  if len(ys):top[ys[0]:min(rh,ys[0]+12),x]=visible[ys[0]:min(rh,ys[0]+12),x]
 clipped_crown=int(np.count_nonzero(top&interior&~coverage))
 overlaps=[]
 for i,a in enumerate(rows):
  ax,ay,aw,ah=a['world_box'];aa=decode(D/a['file'])
  for b in rows[i+1:]:
   bx,by,bw,bh=b['world_box'];x0=max(ax,bx,4220);x1=min(ax+aw,bx+bw,4405);y0=max(ay,by);y1=min(ay+ah,by+bh)
   if x1<=x0 or y1<=y0:continue
   bb=decode(D/b['file']);av=aa[(y0-ay)*4:(y1-ay)*4,(x0-ax)*4:(x1-ax)*4];bv=bb[(y0-by)*4:(y1-by)*4,(x0-bx)*4:(x1-bx)*4]
   mask=(av[:,:,3]==255)&(bv[:,:,3]==255)
   diff=int(np.abs(av[:,:,:3].astype(int)-bv[:,:,:3]).max(axis=2)[mask].max()) if mask.any() else 0
   assert diff==0,(a['object_id'],b['object_id'],diff)
   overlaps.append(dict(objects=[a['object_id'],b['object_id']],opaque_pixels=int(mask.sum()),max_rgb_difference=diff))
 report=dict(updated_sprites=11,unchanged_art_and_exe_files=unchanged,alpha_native_binary=True,alpha_changed_pixels=sum(r['alpha_changed'] for r in rows),crown_pixels_clipped_by_canvas=clipped_crown,shared_render_overlap=overlaps,registry_unchanged=True,exe_unchanged=True)
 save(B/'asset-audit.json',report);print(json.dumps(report))
 assert clipped_crown==0,'Crown still clipped by per-sprite canvas'
if __name__=='__main__':main()
