"""Register authored stone materials to the unchanged CE wall/cap geometry.

The cap and crown use the same periodic world-space material, on the actual
48,-12 / 32,24 square lattice. Alpha and all object metadata are retained.
"""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from scipy import ndimage as nd
from PIL import Image
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
O=R/'assets/generated/v13ent-wall-geometry-kit/v4-crown-20261115'
B=R/'build/hd-wall-crown-v4-20261115';D=W/'runtime/data/art/hd/world-pilot'
LIVE=R/'runtime/hd-world-pilot/data/art/hd/world-pilot';S=R/'assets/generated/v13ent-cave/v1-20261111/sources'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):
 b=p.read_bytes();m,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(h,w,4).copy()
def pack(p,a):p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def ease(a):a=np.clip(a,0,1);return a*a*(3-2*a)
CAP=np.asarray(Image.open(O/'cap-seam-comfy/cap-periodic.png').convert('RGB'),np.float32)
def cap_rgb(wx,wy):
 # Integer quarter-pixel numerators keep samples exact across adjacent tiles
 # and per-object sprites, even far from the map coordinate origin.
 qx=np.rint(wx*4).astype(np.int64);qy=np.rint(wy*4).astype(np.int64)
 u=((3*(qx+64)-4*(qy-40))%768)*(CAP.shape[1]/768.)
 v=((qx+64+4*(qy-40))%512)*(CAP.shape[0]/512.)
 return np.stack([nd.map_coordinates(CAP[:,:,c],[v,u],order=1,mode='grid-wrap') for c in range(3)],axis=-1)
def main():
 ps=read(R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115/inventory.json')['placements']
 sources={a['path']:a for a in read(S/'manifest.json')['assets']}
 x0=min(p['x'] for p in ps)-8;y0=min(p['y'] for p in ps)-8
 ww=max(p['x']+p['width'] for p in ps)-x0+8;hh=max(p['y']+p['height'] for p in ps)-y0+8
 masks={k:np.asarray(Image.open(S/sources[k]['rgba_png']).convert('RGBA'))[:,:,3]>0 for k in {p['source'] for p in ps}}
 occupied=np.zeros((hh,ww),bool);visible=np.zeros_like(occupied);base=np.zeros((hh,ww),np.float32);back=np.zeros_like(base)
 current={}
 for p in ps:
  x,y,w,h=p['x']-x0,p['y']-y0,p['width'],p['height'];m=masks[p['source']]
  occupied[y:y+h,x:x+w]|=m;n=int(Path(p['source']).stem[2:])
  back[y:y+h,x:x+w][m]=float(n==50 or 53<=n<=70)
  slope=.75 if 19<=n<=28 or 59<=n<=65 else -.25
  plane=np.broadcast_to(y+h-1+slope*(np.arange(w,dtype=np.float32)-(w-1)*.5),(h,w))
  base[y:y+h,x:x+w][m]=plane[m]
  name='vault-rock-a.rgba' if p['id']==252 else f'wall-geometry-{p["id"]:04}.rgba'
  a=decode(LIVE/name);current[p['id']]=(name,a)
  visible[y:y+h,x:x+w]|=a[:h*4,:w*4,3].reshape(h,4,w,4).max((1,3))>0
 weight=nd.gaussian_filter(occupied.astype(np.float32),(2.,10.))
 base=nd.gaussian_filter(base*occupied,(2.,10.))/np.maximum(weight,1e-6)
 v=np.clip(1-(base-np.arange(hh,dtype=np.float32)[:,None])/124.,0,1)
 back=nd.gaussian_filter(back*occupied,.7)/np.maximum(nd.gaussian_filter(occupied.astype(np.float32),.7),1e-6)
 support=nd.binary_closing(visible,iterations=2)|visible
 above=np.vstack((np.zeros((1,ww),bool),support[:-1]))
 top=support & ~above & (v<.55)
 actual_top=visible & ~np.vstack((np.zeros((1,ww),bool),visible[:-1]))
 top|=actual_top & nd.maximum_filter(~support,size=3) & (v<.55)
 left=np.hstack((np.zeros((hh,1),bool),support[:,:-1]));right=np.hstack((support[:,1:],np.zeros((hh,1),bool)))
 sides=nd.binary_opening(support & (~left|~right),structure=np.ones((7,1),bool)) & (v<.85)
 dt=nd.distance_transform_edt(~top).astype(np.float32);ds=nd.distance_transform_edt(~sides).astype(np.float32)
 np.savez_compressed(O/'registration-fields.npz',top=top,sides=sides,top_distance=dt,side_distance=ds,visible=visible)
 face=np.asarray(Image.open(O/'wall-material.png').convert('RGB'),np.float32);fh,fw=face.shape[:2]
 (O/'sprites').mkdir(exist_ok=True);(B/'review').mkdir(parents=True,exist_ok=True)
 records=[];preview=Image.new('RGBA',(ww*2,hh*2))
 for p in ps:
  h,w=p['height'],p['width'];yy,xx=np.mgrid[:h*4,:w*4].astype(np.float32)
  wx=xx*.25+p['x'];wy=yy*.25+p['y'];gx=wx-x0;gy=wy-y0
  vv=nd.map_coordinates(v,[gy,gx],order=1,mode='nearest');rear=nd.map_coordinates(back,[gy,gx],order=1,mode='nearest')
  distance=nd.map_coordinates(dt,[gy,gx],order=1,mode='nearest');side=nd.map_coordinates(ds,[gy,gx],order=1,mode='nearest')
  # Keep the prior face coordinates; no broad 22px UV pull toward the edge.
  u=((wx+wy*.22)*3.1)%(2*(fw-1));u=np.where(u>fw-1,2*(fw-1)-u,u)
  rgb=np.stack([nd.map_coordinates(face[:,:,c],[vv*(fh-1),u],order=1,mode='nearest') for c in range(3)],axis=-1)
  lighting=(1-rear*.63)*.88
  # A short contact crease below the 5.5px top plane, not a dark gradient rim.
  crease=1-.23*(1-ease((distance-7)/3.5))
  lighting*=np.where(distance>6,crease,1)
  lighting*=.78+.22*ease(side/4.)
  rgb*=lighting[:,:,None]
  cap=cap_rgb(wx,wy)
  join=ease((distance-5.5)/.75)[:,:,None]
  rgb=cap*(1-join)+rgb*join
  name,old=current[p['id']];a=old.copy();a[:h*4,:w*4,:3]=np.clip(np.rint(rgb),0,255)
  assert np.array_equal(a[:,:,3],old[:,:,3])
  pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
  obj=next(o for o in sources[p['source']]['map_instances'] if o['id']==p['id'])
  records.append(dict(kind='wall',object=obj,source=p['source'],world_box=[p['x'],p['y'],w,h],file=name,png=str(png.relative_to(R)),before_sha256=sha(LIVE/name),sha256=sha(D/name),alpha_exact=True))
  im=Image.fromarray(a[:h*4,:w*4]).resize((w*2,h*2),Image.Resampling.NEAREST)
  preview.alpha_composite(im,((p['x']-x0)*2,(p['y']-y0)*2))
 # All cap identities use the same periodic field. Their existing alpha and
 # registry slots remain intact, so all variant toggles also join correctly.
 for id in [61,62,63]:
  for name in [f'asset-{id:03}.rgba']+([f'tile-{id:03}-v{s}.rgba' for s in [1,2,3]] if id!=61 else []):
   old=decode(LIVE/name);a=old.copy();yy,xx=np.mgrid[:a.shape[0],:a.shape[1]]
   a[:,:,:3]=np.clip(np.rint(cap_rgb(xx*.25-16,yy*.25-2)),0,255)
   pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
   records.append(dict(kind='cap',asset_id=id,source=f'art/tiles/cav{4008+id-61}.frm',file=name,png=str(png.relative_to(R)),before_sha256=sha(LIVE/name),sha256=sha(D/name),alpha_exact=True))
 preview.thumbnail((2200,1600));preview.save(B/'review/registered-wall-map.png')
 save(O/'placements.json',dict(status='prototype pending SDL review',images=records,wall_placements=418,cap_images=9,source_wall_types=62,cap_plane_width_native=5.5,transition_native=.75,alpha_exact=True,registration_unchanged=True,world_origin=[x0,y0],cap_lattice=[[48,-12],[32,24]],note='Cap variants share one continuous material; this stage adds a readable solid cut surface, not independently random top tiles.'))
 print('Baked',len(records),'images with solid stone top; unchanged alpha and registration')
if __name__=='__main__':main()
