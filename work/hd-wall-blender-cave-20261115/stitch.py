"""Assemble calibrated render regions with a shared world-coordinate overlap."""
from prepare import *
def main():
 plan=read(O/'tile-layout.json');box=plan['box'];s=plan['scale'];h=(box[3]-box[1])*s;w=(box[2]-box[0])*s
 rgb=np.zeros((h,w,3),np.float32);alpha=np.zeros((h,w),np.float32);weight=np.zeros((h,w),np.float32)
 for t in plan['tiles']:
  a=np.asarray(Image.open(O/(t['name']+'.png')).convert('RGBA'),np.float32);b=t['box'];core=t['core']
  x0=max(b[0],box[0]);y0=max(b[1],box[1]);x1=min(b[2],box[2]);y1=min(b[3],box[3])
  a=a[(y0-b[1])*s:(y1-b[1])*s,(x0-b[0])*s:(x1-b[0])*s]
  xx=np.arange(a.shape[1])/s+x0;yy=np.arange(a.shape[0])/s+y0
  # Flat weight over the core; smooth falloff only in the shared render border.
  fx=np.clip(np.minimum((xx-b[0])/32,(b[2]-xx)/32),0,1);fy=np.clip(np.minimum((yy-b[1])/32,(b[3]-yy)/32),0,1)
  f=(fy*fy*(3-2*fy))[:,None]*(fx*fx*(3-2*fx))[None,:];al=a[:,:,3]/255
  sl=(slice((y0-box[1])*s,(y1-box[1])*s),slice((x0-box[0])*s,(x1-box[0])*s))
  rgb[sl]+=a[:,:,:3]*(f*al)[:,:,None];alpha[sl]+=f*al;weight[sl]+=f
  t['sha256']=sha(O/(t['name']+'.png'))
 out=np.zeros((h,w,4),np.uint8);out[:,:,:3]=np.clip(np.rint(rgb/np.maximum(alpha[:,:,None],1e-8)),0,255)
 out[:,:,3]=np.clip(np.rint(255*alpha/np.maximum(weight,1e-8)),0,255)
 Image.fromarray(out).save(O/'cave-render.png')
 save(O/'tile-layout.json',plan);camera=read(O/(plan['tiles'][0]['name']+'-camera.json'))
 camera.update(box=box,scale=4,render_regions=len(plan['tiles']),overlap_native_pixels=64,compositing='Premultiplied-alpha weighted overlap; no color correction or image warp')
 save(O/'cave-render-camera.json',camera)
 print('Assembled',len(plan['tiles']),'calibrated regions into',w,h)
if __name__=='__main__':main()
