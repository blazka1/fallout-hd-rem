"""Cut the common camera render into the existing 417 registered canvases."""
from prepare import *
from cap import sample
def ease(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def quantize(a):
 a=a.copy();h,w=a.shape[:2];aa=a[:,:,3].astype(float)/255
 blocks=aa.reshape(h//4,4,w//4,4);valid=blocks.mean((1,3))>=.5
 a[:,:,3]=np.repeat(np.repeat(valid,4,0),4,1)*255
 # Extend edge color inside its own logical 4x4 cell; identical on overlaps.
 rgb=a[:,:,:3].astype(float)*aa[:,:,None]
 mean=rgb.reshape(h//4,4,w//4,4,3).sum((1,3))/np.maximum(blocks.sum((1,3))[:,:,None],1e-8)
 fill=np.repeat(np.repeat(mean,4,0),4,1)
 empty=(aa<.01)&(a[:,:,3]>0);a[:,:,:3][empty]=np.clip(np.rint(fill[empty]),0,255)
 return a
def main():
 import sys
 inv=read(O/'inventory.json');box=inv['box'];preflight='--preflight' in sys.argv
 source=O/('overview.png' if preflight else 'cave-render.png');render=Image.open(source).convert('RGBA')
 if preflight:render=render.resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST)
 assert render.size==((box[2]-box[0])*4,(box[3]-box[1])*4)
 rows=[];(O/'sprites').mkdir(exist_ok=True)
 cap=np.asarray(Image.open(O/'cap-periodic.png').convert('RGB'),float);guides=np.load(O/'mesh-guides.npz');top=guides['top']
 for p in inv['placements']:
  if p['id']==252:continue
  x,y,w,h=p['x'],p['y'],p['width'],p['height'];name=f'wall-geometry-{p["id"]:04}.rgba'
  old=decode(LIVE/'data/art/hd/world-pilot'/name)
  a=quantize(np.asarray(render.crop(((x-box[0])*4,(y-box[1])*4,(x+w-box[0])*4,(y+h-box[1])*4))))
  yy,xx=np.mgrid[:h*4,:w*4];wx=x+xx/4;wy=y+yy/4
  ty=nd.map_coordinates(top,[wy-box[1],wx-box[0]],order=1,mode='nearest')
  blend=(1-ease((wy-ty-2)/6))[:,:,None]
  a[:,:,:3]=np.clip(np.rint(a[:,:,:3]*(1-blend)+sample(cap,wx,wy)*blend),0,255)
  assert a.shape==old.shape
  pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
  rows.append(dict(kind='wall',object_id=p['id'],file=name,world_box=[x,y,w,h],source=p['source'],png=str(png.relative_to(R)),before_sha256=sha(LIVE/'data/art/hd/world-pilot'/name),sha256=sha(D/name),alpha_changed=int(np.count_nonzero(old[:,:,3]!=a[:,:,3]))))
 for aid in [61,62,63]:
  for name in [f'asset-{aid:03}.rgba']+([f'tile-{aid:03}-v{s}.rgba' for s in [1,2,3]] if aid!=61 else []):
   old=decode(LIVE/'data/art/hd/world-pilot'/name);a=old.copy();yy,xx=np.mgrid[:a.shape[0],:a.shape[1]]
   a[:,:,:3]=np.clip(np.rint(sample(cap,xx*.25-16,yy*.25-2)),0,255)
   pack(D/name,a);png=O/'sprites'/(Path(name).stem+'.png');Image.fromarray(a).save(png)
   rows.append(dict(kind='cap',asset_id=aid,file=name,png=str(png.relative_to(R)),before_sha256=sha(LIVE/'data/art/hd/world-pilot'/name),sha256=sha(D/name),alpha_changed=0))
 save(O/'placement-slices.json',dict(images=rows,render_sha256=sha(source),preflight_only=preflight,alpha='Calibrated continuous Blender surface, quantized to CE native grid',protected_door_object=252))
 print('Packed',len(rows),'images: 417 registered walls + 9 cap tiles')
if __name__=='__main__':main()
