"""Prepare continuous projected footprint guides, not an image texture atlas.

The Blender mesh reconstructs vertical stone faces and a shared upper bevel
from these guides. Every sprite will be cut from the same camera render.
"""
from prepare import *
def main():
 inv=read(O/'inventory.json');x0,y0,x1,y1=inv['box'];f=np.load(O/'reference-fields.npz');canvas=f['canvas']
 # Close source pixel teeth/gaps into supported boundaries. Canvas constraints
 # are kept; original alpha is not stamped onto the rendered sprite.
 mask=nd.gaussian_filter(nd.binary_closing(f['mask'],iterations=2).astype(float),1.15)>.43
 # Reserve one logical pixel around the OUTER canvas union. Neighboring
 # sprites still share their full interior overlap; this is not per-tile erosion.
 mask &= nd.binary_erosion(canvas,iterations=1)
 top=np.zeros(mask.shape,np.float32);bottom=np.zeros_like(top)
 for x in range(mask.shape[1]):
  q=np.flatnonzero(np.diff(np.r_[False,mask[:,x],False].astype(int))); 
  for a,b in zip(q[::2],q[1::2]):
   if b-a<12:mask[a:b,x]=False;continue
   top[a:b,x]=a+y0;bottom[a:b,x]=b+y0-1
 weight=nd.gaussian_filter(mask.astype(float),(3.,5.))
 for a in [top,bottom]:a[:]=nd.gaussian_filter(a*mask,(3.,5.))/np.maximum(weight,1e-8)
 # Horizontal derivative gives the actual cave run direction in ground space.
 by=(nd.gaussian_filter(bottom*mask,(2.,7.))/np.maximum(nd.gaussian_filter(mask.astype(float),(2.,7.)),1e-8))
 deriv=np.clip(np.gradient(by,axis=1),-3,3)
 dist=nd.distance_transform_edt(mask).astype(np.float32)
 np.savez_compressed(O/'mesh-guides.npz',mask=mask,top=top,bottom=bottom,deriv=deriv,distance=dist)
 save(O/'geometry-contract.json',dict(box=inv['box'],scale=4,original_registration_retained=True,original_alpha_stamped=False,mesh='One continuous sculpt with shared vertex indices; cap and face share vertices',material='Accepted blender-corner-v2 rock material',variation='continuous broad ridges plus seeded sparse open faults',protected_door_object=252))
 print('Prepared',int(mask.sum()),'native mesh samples')
if __name__=='__main__':main()
