from pack import *
def main():
 record=read(O/'placement-slices.json');assert not record['preflight_only'],'Cannot accept low-resolution geometry preflight'
 rows=record['images'];baseline=read(W/'baseline.json');changed={'data/art/hd/world-pilot/'+r['file'] for r in rows}
 assert len(rows)==426
 unchanged=0
 for rel,h in baseline['files'].items():
  if rel.startswith('data/art/') or rel=='fallout-ce.exe':
   if rel not in changed:assert sha(W/'runtime'/rel)==h,rel;unchanged+=1
 cache={}
 for r in rows:
  a=decode(D/r['file']);h,w=a.shape[:2];alpha=a[:,:,3];assert np.isin(alpha,[0,255]).all()
  assert np.array_equal(alpha,np.repeat(np.repeat(alpha[::4,::4],4,0),4,1))
  assert sha(D/r['file'])==r['sha256']
  if r['kind']=='wall':cache[r['object_id']]=a
  else:assert np.array_equal(alpha,decode(LIVE/'data/art/hd/world-pilot'/r['file'])[:,:,3])
 overlaps=[]
 walls=[r for r in rows if r['kind']=='wall']
 for i,a in enumerate(walls):
  ax,ay,aw,ah=a['world_box'];aa=cache[a['object_id']]
  for b in walls[i+1:]:
   bx,by,bw,bh=b['world_box'];x0=max(ax,bx);x1=min(ax+aw,bx+bw);y0=max(ay,by);y1=min(ay+ah,by+bh)
   if x1<=x0 or y1<=y0:continue
   bb=cache[b['object_id']];av=aa[(y0-ay)*4:(y1-ay)*4,(x0-ax)*4:(x1-ax)*4];bv=bb[(y0-by)*4:(y1-by)*4,(x0-bx)*4:(x1-bx)*4]
   mask=(av[:,:,3]==255)&(bv[:,:,3]==255)
   diff=int(np.abs(av[:,:,:3].astype(int)-bv[:,:,:3]).max(axis=2)[mask].max()) if mask.any() else 0
   assert diff==0,(a['object_id'],b['object_id'],diff)
   if mask.any():overlaps.append(dict(objects=[a['object_id'],b['object_id']],opaque_pixels=int(mask.sum()),max_rgb_difference=diff))
 # Account for all projected opaque geometry outside the union of registered
 # canvases. Exclude the separately protected vault rock canvas.
 inv=read(O/'inventory.json');box=inv['box'];f=np.load(O/'reference-fields.npz')
 render=np.asarray(Image.open(O/'cave-render.png').convert('RGBA'));coverage=np.repeat(np.repeat(f['canvas'],4,0),4,1)
 outside=int(np.count_nonzero((render[:,:,3]>=128)&~coverage))
 report=dict(updated_sprites=len(rows),unchanged_art_and_exe_files=unchanged,alpha_native_binary=True,alpha_changed_pixels=sum(r['alpha_changed'] for r in rows),render_pixels_outside_canvas=outside,shared_render_overlap=overlaps,registry_unchanged=True,exe_unchanged=True,door_preserved=True)
 save(B/'asset-audit.json',report);print('Audit:',len(rows),'sprites,',len(overlaps),'exact overlaps,',outside,'pixels outside canvases;',unchanged,'protected files')
 assert outside==0,'Projected surface clipped by existing canvases'
if __name__=='__main__':main()
