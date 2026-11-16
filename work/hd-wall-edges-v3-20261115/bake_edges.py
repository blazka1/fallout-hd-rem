"""Register an authored crown to the shared wall boundary; preserve every alpha.

Artwork: ImageGen edit + native ComfyUI atlas composition. This script computes
texture coordinates, applies the existing face lighting and packs original-size
F1HD images. It does not draw new rock shapes or procedural texture noise.
"""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from scipy import ndimage as nd
from PIL import Image
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
MASTER=R/'assets/generated/v13ent-wall-geometry-kit/v3-edges-20261115'
O=MASTER/'registered-v2'
S=R/'assets/generated/v13ent-cave/v1-20261111/sources'
D=W/'runtime/data/art/hd/world-pilot';B=R/'build/hd-wall-edges-v3-20261115'
LIVE=R/'runtime/hd-world-pilot/data/art/hd/world-pilot'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):
 b=p.read_bytes();m,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(h,w,4).copy()
def pack(p,a):p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def ease(x):x=np.clip(x,0.,1.);return x*x*(3.-2.*x)
def main():
 O.mkdir(parents=True,exist_ok=True)
 ps=read(R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115/inventory.json')['placements']
 sources={a['path']:a for a in read(S/'manifest.json')['assets']}
 x0=min(p['x'] for p in ps)-8;y0=min(p['y'] for p in ps)-8
 ww=max(p['x']+p['width'] for p in ps)-x0+8;hh=max(p['y']+p['height'] for p in ps)-y0+8
 masks={k:np.asarray(Image.open(S/sources[k]['rgba_png']).convert('RGBA'))[:,:,3]>0 for k in {p['source'] for p in ps}}
 occupancy=np.zeros((hh,ww),bool);visible=np.zeros_like(occupancy)
 back=np.zeros((hh,ww),np.float32);base=np.zeros_like(back)
 current={}
 for p in ps:
  x,y,w,h=p['x']-x0,p['y']-y0,p['width'],p['height'];m=masks[p['source']]
  occupancy[y:y+h,x:x+w]|=m
  n=int(Path(p['source']).stem[2:]);back[y:y+h,x:x+w][m]=float(n==50 or 53<=n<=70)
  slope=.75 if 19<=n<=28 or 59<=n<=65 else -.25
  plane=np.broadcast_to(y+h-1+slope*(np.arange(w,dtype=np.float32)-(w-1)*.5),(h,w))
  base[y:y+h,x:x+w][m]=plane[m]
  name='vault-rock-a.rgba' if p['id']==252 else f'wall-geometry-{p["id"]:04}.rgba'
  a=decode(LIVE/name);current[p['id']]=(name,a)
  # Sample the already installed combined silhouette, not each narrow FRM edge.
  alpha=a[:h*4,:w*4,3].reshape(h,4,w,4).max((1,3))>0
  visible[y:y+h,x:x+w]|=alpha
 weight=nd.gaussian_filter(occupancy.astype(np.float32),(2.,10.))
 base=nd.gaussian_filter(base*occupancy,(2.,10.))/np.maximum(weight,1e-6)
 v=np.clip(1.-(base-np.arange(hh,dtype=np.float32)[:,None])/124.,0.,1.)
 back=nd.gaussian_filter(back*occupancy,.7)/np.maximum(nd.gaussian_filter(occupancy.astype(np.float32),.7),1e-6)
 # Ignore tiny FRM pinholes when defining the crown, while keeping actual alpha
 # bit-identical. Closing is used only for the coordinate guide, never visibility.
 support=nd.binary_closing(visible,iterations=2)|visible
 above=np.zeros_like(support);above[1:]=support[:-1]
 left=np.zeros_like(support);left[:,1:]=support[:,:-1]
 right=np.zeros_like(support);right[:,:-1]=support[:,1:]
 top=support & ~above & (v<.55)
 sides=nd.binary_opening(support & (~left|~right),structure=np.ones((7,1),bool)) & (v<.85)
 boundary=top|sides
 distance=nd.distance_transform_edt(~boundary).astype(np.float32)
 # Outline of the actual visible union can be 1-2 px away from the guide after
 # hole closing. Include exposed top pixels adjacent to the exterior background.
 outside=~support
 actual_top=visible & ~np.vstack((np.zeros((1,ww),bool),visible[:-1]))
 exterior_near=nd.maximum_filter(outside,size=3)
 boundary|=actual_top & exterior_near & (v<.55)
 distance=nd.distance_transform_edt(~boundary).astype(np.float32)
 np.savez_compressed(O/'registration-fields.npz',boundary=boundary,distance=distance,visible=visible)
 atlas=np.asarray(Image.open(MASTER/'edge-guard-comfy/edge-relief-guarded.png').convert('RGB'),np.float32)
 ah,aw=atlas.shape[:2];assert np.all(atlas[:8]==34)
 (O/'sprites').mkdir(exist_ok=True);(B/'review').mkdir(parents=True,exist_ok=True)
 preview=Image.new('RGBA',(ww*2,hh*2));records=[];edge_before=[];edge_after=[]
 for p in ps:
  h,w=p['height'],p['width'];yy,xx=np.mgrid[:h*4,:w*4].astype(np.float32)
  gx=xx*.25+p['x']-x0;gy=yy*.25+p['y']-y0
  vv=nd.map_coordinates(v,[gy,gx],order=1,mode='nearest')
  rear=nd.map_coordinates(back,[gy,gx],order=1,mode='nearest')
  dist=nd.map_coordinates(distance,[gy,gx],order=1,mode='nearest')
  crown=ease(dist/22.)
  av=vv*crown*(ah-1)
  u=((gx+x0+(gy+y0)*.22)*3.1)%(2*(aw-1));u=np.where(u>aw-1,2*(aw-1)-u,u)
  rgb=np.stack([nd.map_coordinates(atlas[:,:,c],[av,u],order=1,mode='nearest') for c in range(3)],axis=2)
  # Return planes join RGB34 cutaways under the same game light. Fade only the
  # previous orientation factor toward the boundary, not two competing artworks.
  rgb*=(1.+(((1.-rear*.63)*.88)-1.)*crown)[:,:,None]
  name,old=current[p['id']];a=old.copy();a[:h*4,:w*4,:3]=np.clip(np.rint(rgb),0,255)
  edge=(dist==0)&(a[:h*4,:w*4,3]>0)
  edge_before.extend(np.abs(old[:h*4,:w*4,:3][edge].astype(np.int16)-34).mean(1).tolist())
  edge_after.extend(np.abs(a[:h*4,:w*4,:3][edge].astype(np.int16)-34).mean(1).tolist())
  assert np.array_equal(a[:,:,3],old[:,:,3])
  pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
  obj=next(o for o in sources[p['source']]['map_instances'] if o['id']==p['id'])
  records.append(dict(object=obj,source=p['source'],world_box=[p['x'],p['y'],w,h],file=name,png=str(png.relative_to(R)),before_sha256=sha(LIVE/name),sha256=sha(D/name),alpha_exact=True))
  im=Image.fromarray(a[:h*4,:w*4]).resize((w*2,h*2),Image.Resampling.NEAREST)
  preview.alpha_composite(im,((p['x']-x0)*2,(p['y']-y0)*2))
 preview.thumbnail((2200,1600));preview.save(B/'review/registered-wall-map.png')
 save(O/'placements.json',dict(status='candidate pending real SDL review',placements=records,source_types=62,registration_unchanged=True,alpha_unchanged=True,world_origin=[x0,y0],boundary_transition_native_px=22,edge_samples=len(edge_after),mean_unlit_boundary_difference_before=float(np.mean(edge_before)),mean_unlit_boundary_difference_after=float(np.mean(edge_after)),maximum_unlit_boundary_difference_after=float(max(edge_after)),note='Boundary color metric compares authored RGB with cap RGB34 before runtime lighting; gameplay captures remain the visual acceptance test.'))
 print('Prepared',len(records),'images; exact alpha. Boundary RGB error',round(np.mean(edge_before),2),'->',max(edge_after))
if __name__=='__main__':main()
