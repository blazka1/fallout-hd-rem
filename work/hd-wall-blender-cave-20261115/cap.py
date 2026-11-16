"""Periodic bake registration for shared wall crowns and existing floor caps."""
from prepare import *
def periodic(a):
 # Periodic + smooth decomposition removes only the low-frequency boundary
 # mismatch of the Blender material bake; the rock detail is retained.
 h,w,c=a.shape;v=np.zeros_like(a,dtype=float)
 v[0]+=a[-1]-a[0];v[-1]-=a[-1]-a[0]
 v[:,0]+=a[:,-1]-a[:,0];v[:,-1]-=a[:,-1]-a[:,0]
 den=(2*np.cos(2*np.pi*np.arange(w)/w)[None,:]+2*np.cos(2*np.pi*np.arange(h)/h)[:,None]-4);den[0,0]=1
 sf=np.fft.fft2(v,axes=(0,1))/den[:,:,None];sf[0,0]=0
 return np.clip(a-np.fft.ifft2(sf,axes=(0,1)).real,0,255)
def sample(cap,wx,wy):
 qx=np.rint(wx*4).astype(np.int64);qy=np.rint(wy*4).astype(np.int64)
 u=((3*(qx+64)-4*(qy-40))%768)*(cap.shape[1]/768.)
 v=((qx+64+4*(qy-40))%512)*(cap.shape[0]/512.)
 return np.stack([nd.map_coordinates(cap[:,:,c],[v,u],order=1,mode='grid-wrap') for c in range(3)],axis=-1)
def main():
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='reference':
  a=np.asarray(Image.open(O/'reference-rock-detail.png').convert('RGB')).astype(float)
  Image.fromarray(np.rint(periodic(a)).astype(np.uint8)).save(O/'reference-rock-periodic.png');return
 a=np.asarray(Image.open(O/'cap-material-raw.png').convert('RGB')).astype(float)
 p=periodic(a);Image.fromarray(np.rint(p).astype(np.uint8)).save(O/'cap-periodic.png')
 yy,xx=np.mgrid[:88,:112];base=sample(p,xx/4+3900,yy/4+400)
 for dx,dy in [(48,-12),(32,24)]:assert np.array_equal(base,sample(p,xx/4+3900+dx,yy/4+400+dy))
 save(O/'cap-material-provenance.json',dict(source='cap-material.blend',shader='Exact accepted corner rock shader on a horizontal plane',registration='48,-12 / 32,24 lattice, same quarter-pixel world phase on caps and crowns',periodic_decomposition=True,median_rgb=np.median(p,axis=(0,1)).tolist(),translation_checks=2))
 print('Prepared periodic Blender cap; median',np.median(p,axis=(0,1)))
if __name__=='__main__':main()
