"""Bake an ImageGen relief atlas onto the original connected wall footprint.

This is registration/texture-coordinate rasterization, not procedural artwork.
Every overlapping fragment samples one shared field; no A/B/C image blending.
"""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from scipy import ndimage as nd
from PIL import Image
R=Path(__file__).resolve().parents[2]; W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-geometry-kit/v2-registered-20261115'
S=R/'assets/generated/v13ent-cave/v1-20261111/sources'
D=W/'runtime/data/art/hd/world-pilot'; B=R/'build/hd-wall-geometry-live-20261115'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def pack(p,a):p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def decode(p):
 b=p.read_bytes();m,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(h,w,4).copy()
def main():
 inv=read(R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115/inventory.json')
 sources={a['path']:a for a in read(S/'manifest.json')['assets']}; ps=inv['placements']
 x0=min(p['x'] for p in ps)-8;y0=min(p['y'] for p in ps)-8
 ww=max(p['x']+p['width'] for p in ps)-x0+8;hh=max(p['y']+p['height'] for p in ps)-y0+8
 masks={k:np.asarray(Image.open(S/sources[k]['rgba_png']).convert('RGBA'))[:,:,3]>0 for k in {p['source'] for p in ps}}
 occupancy=np.zeros((hh,ww),bool); back=np.zeros((hh,ww),np.float32);base_field=np.zeros((hh,ww),np.float32)
 for p in ps:
  x=p['x']-x0;y=p['y']-y0;h=p['height'];w=p['width'];m=masks[p['source']]
  occupancy[y:y+h,x:x+w]|=m
  n=int(Path(p['source']).stem[2:]);back[y:y+h,x:x+w][m]=float(n==50 or 53<=n<=70)
  slope=.75 if 19<=n<=28 or 59<=n<=65 else -.25
  plane=np.broadcast_to(y+h-1+slope*(np.arange(w,dtype=np.float32)-(w-1)*.5),(h,w))
  base_field[y:y+h,x:x+w][m]=plane[m]
 # Remove only unsupported narrow contour spikes. Intersecting with the original
 # union forbids expanding walls into any formerly empty floor/door pixel.
 opened=nd.binary_opening(occupancy,structure=nd.generate_binary_structure(2,1),iterations=2)
 shape=opened & occupancy
 # Keep the exact approved door-side shape; its own alpha is applied separately.
 door=next(p for p in ps if p['id']==252)
 dx,dy=door['x']-x0,door['y']-y0
 shape[dy:dy+door['height'],dx:dx+door['width']]=occupancy[dy:dy+door['height'],dx:dx+door['width']]
 # Shared affine wall-height coordinate, anchored to original floor supports.
 # No per-column stretching around old holes or ragged silhouette boundaries.
 weight=nd.gaussian_filter(occupancy.astype(np.float32),(2.,10.))
 base_field=nd.gaussian_filter(base_field*occupancy,(2.,10.))/np.maximum(weight,1e-6)
 yy=np.arange(hh,dtype=np.float32)[:,None]
 v=np.clip(1.-(base_field-yy)/124.,0.,1.)
 # These fields describe registration and face orientation, not generated RGB.
 back=nd.gaussian_filter(back*occupancy,.7)/np.maximum(nd.gaussian_filter(occupancy.astype(np.float32),.7),1e-6)
 atlas=np.asarray(Image.open(O/'relief-atlas.png').convert('RGB'),np.float32)
 ah,aw=atlas.shape[:2]; records=[];rows=['# object fid pid tile elevation x y rotation width height filename']
 (O/'sprites').mkdir(exist_ok=True);(B/'review').mkdir(parents=True,exist_ok=True)
 # Bake each sprite directly from the same global subpixel coordinate field.
 # Identical world-space samples guarantee exact RGB equality at overlaps.
 def render(p):
  h,w=p['height'],p['width'];yy,xx=np.mgrid[0:h*4,0:w*4].astype(np.float32)
  gx=xx*.25+p['x']-x0;gy=yy*.25+p['y']-y0
  vv=nd.map_coordinates(v,[gy,gx],order=1,mode='nearest')
  rear=nd.map_coordinates(back,[gy,gx],order=1,mode='nearest')
  # Mirrored extension has identical boundary samples, unlike wrap tiling.
  u=((gx+x0+(gy+y0)*.22)*3.1)%(2*(aw-1));u=np.where(u>aw-1,2*(aw-1)-u,u)
  av=np.clip(vv,0,1)*(ah-1)
  rgb=np.stack([nd.map_coordinates(atlas[:,:,c],[av,u],order=1,mode='nearest') for c in range(3)],axis=2)
  rgb*=((1.-rear*.63)*.88)[:,:,None]
  alpha=np.repeat(np.repeat(masks[p['source']],4,0),4,1)
  allowed=shape[p['y']-y0:p['y']-y0+h,p['x']-x0:p['x']-x0+w]
  alpha &= np.repeat(np.repeat(allowed,4,0),4,1)
  a=np.empty((h*4,w*4,4),np.uint8);a[:,:,:3]=np.clip(np.rint(rgb),0,255);a[:,:,3]=alpha*255
  return a
 preview=Image.new('RGBA',(ww*2,hh*2))
 for p in ps:
  a=render(p);s=sources[p['source']];obj=next(o for o in s['map_instances'] if o['id']==p['id'])
  if p['id']==252:
   old=decode(D/'vault-rock-a.rgba');old[:p['height']*4,:p['width']*4,:3]=a[:,:,:3]
   pack(D/'vault-rock-a.rgba',old);Image.fromarray(old).save(O/'vault-rock-a.png')
   a[:,:,3]=old[:p['height']*4,:p['width']*4,3]
  else:
   fn=f'wall-geometry-{p["id"]:04}.rgba';pack(D/fn,a)
   Image.fromarray(a).save(O/'sprites'/f'wall-{p["id"]:04}.png')
   rows.append(' '.join(map(str,[obj['id'],obj['fid'],obj['pid'],obj['tile'],obj['elevation'],obj['x'],obj['y'],obj['rotation'],p['width'],p['height'],fn])))
   records.append(dict(object=obj,source=p['source'],world_box=[p['x'],p['y'],p['width'],p['height']],file=fn,sha256=hashlib.sha256((D/fn).read_bytes()).hexdigest(),registration=s['registration']))
  im=Image.fromarray(a).resize((p['width']*2,p['height']*2),Image.Resampling.NEAREST)
  preview.alpha_composite(im,((p['x']-x0)*2,(p['y']-y0)*2))
 (D/'wall-geometry.tsv').write_text('\n'.join(rows)+'\n',encoding='ascii')
 preview.thumbnail((2200,1600));preview.save(B/'review/registered-wall-map.png')
 save(O/'placements.json',dict(status='registered candidate pending SDL review',source_types=62,placements=records,approved_door_alpha_preserved=True,world_origin=[x0,y0],global_bounds=[ww,hh],original_mask_pixels=int(occupancy.sum()),new_mask_pixels=int(shape.sum()),global_rule='Shared world-space atlas coordinates; no RGB blends between variants; no expansion beyond original occupied footprint',art_source='relief-atlas.png'))
 print('Baked',len(records),'placement sprites plus approved door alpha,',sum((D/r['file']).stat().st_size for r in records)//1048576,'MiB')
if __name__=='__main__':main()
