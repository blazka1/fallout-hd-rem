"""Slice one calibrated Blender render into registered CE wall canvases."""
from prepare import *
import struct,numpy as np
from scipy import ndimage as nd
D=W/'runtime/data/art/hd/world-pilot'
SELECT={328,327,350,349,366,365,351,415,434,452,463}
def decode(p):
 b=p.read_bytes();m,v,w,h,c=struct.unpack('<4sIIII',b[:20]);assert (m,v,c)==(b'F1HD',1,4)
 return np.frombuffer(b[20:],np.uint8).reshape(h,w,4).copy()
def pack(p,a):p.write_bytes(struct.pack('<4sIIII',b'F1HD',1,a.shape[1],a.shape[0],4)+a.tobytes())
def ease(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def main():
 reg=read(O/'scene-registration.json');box=reg['box'];render=np.asarray(Image.open(O/'corner-render.png').convert('RGBA'))
 assert tuple(render.shape[:2])==((box[3]-box[1])*4,(box[2]-box[0])*4)
 ps=read(O/'reference-placements.json')['placements'];rows=[];(O/'sprites').mkdir(exist_ok=True)
 for p in ps:
  if p['id'] not in SELECT:continue
  name=f'wall-geometry-{p["id"]:04}.rgba';old=decode(LIVE/'data/art/hd/world-pilot'/name);a=old.copy();h,w=a.shape[:2]
  # Attach to the surrounding V4 stone, avoiding accumulated translucent
  # remnants of the rejected V1 plates at the two blend endpoints.
  attach=decode(R/'build/backups/before-blender-corner-v1-20261115'/name)
  yy,xx=np.mgrid[:h,:w];wx=p['x']+xx/4;wy=p['y']+yy/4
  rx=(wx-box[0])*4;ry=(wy-box[1])*4;inside=(rx>=0)&(rx<render.shape[1])&(ry>=0)&(ry<render.shape[0]);new=np.zeros_like(a)
  new[inside]=render[ry[inside].astype(int),rx[inside].astype(int)]
  blend=ease((wx-4192)/28)*ease((4433-wx)/28)
  # Only the two open ends transition to the existing cave. Interior surface
  # and alpha come directly from the 3D render, with no old-silhouette stamp.
  aa=attach[:,:,3].astype(float)/255;ab=new[:,:,3].astype(float)/255;alpha=aa*(1-blend)+ab*blend
  rgb=attach[:,:,:3]*aa[:,:,None]*(1-blend[:,:,None])+new[:,:,:3]*ab[:,:,None]*blend[:,:,None]
  a[:,:,:3]=np.clip(np.rint(rgb/np.maximum(alpha[:,:,None],1e-8)),0,255).astype(np.uint8)
  # Existing CE wall loader requires one binary alpha per original pixel.
  # Quantize the NEW projected silhouette, not the old FRM silhouette.
  native=alpha.reshape(h//4,4,w//4,4).mean((1,3))>=.5
  a[:,:,3]=np.repeat(np.repeat(native,4,0),4,1)*255
  empty=(alpha<.01)&(a[:,:,3]>0)
  if empty.any():
   near=nd.distance_transform_edt(alpha<.01,return_distances=False,return_indices=True)
   a[:,:,:3][empty]=a[:,:,:3][near[0][empty],near[1][empty]]
  assert np.isin(a[:,:,3],[0,255]).all()
  pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
  rows.append(dict(object_id=p['id'],file=name,world_box=[p['x'],p['y'],p['width'],p['height']],source=p['source'],png=str(png.relative_to(R)),before_sha256=sha(LIVE/'data/art/hd/world-pilot'/name),sha256=sha(D/name),alpha_changed=int(np.count_nonzero(old[:,:,3]!=a[:,:,3]))))
 save(O/'placement-slices.json',dict(images=rows,render_sha256=sha(O/'corner-render.png'),blend_ends=[4192,4220,4405,4433],alpha='From calibrated 3D render, quantized per native pixel for existing CE loader; old canvas and registration retained'))
 print('Packed',len(rows),'wall slices; alpha changes:',sum(r['alpha_changed'] for r in rows))
if __name__=='__main__':main()
