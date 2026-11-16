"""Make a periodic cap material with native Comfy nodes, keeping border detail."""
from pathlib import Path
import importlib.util
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/v13ent-wall-geometry-kit/v4-crown-20261115'
spec=importlib.util.spec_from_file_location('h',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.OUT=O
d=O/'cap-seam-comfy'
if (d/'run.json').exists():h.execute(d,{},{});raise SystemExit
g={}
def add(t,**kw):n=str(len(g)+1);g[n]=h.node(t,**kw);return [n,0]
src=add('LoadImage',image=h.upload(O/'cap-material.png'))
src=add('ImageScale',image=src,upscale_method='lanczos',width=512,height=512,crop='disabled')
blank=add('EmptyImage',width=512,height=512,batch_size=1,color=0)
zero=add('SolidMask',value=0.,width=512,height=512)
for axis in ['x','y']:
 a=add('ImageCrop',image=src,x=256 if axis=='x' else 0,y=256 if axis=='y' else 0,width=256 if axis=='x' else 512,height=256 if axis=='y' else 512)
 b=add('ImageCrop',image=src,x=0,y=0,width=256 if axis=='x' else 512,height=256 if axis=='y' else 512)
 shifted=add('ImageCompositeMasked',destination=blank,source=a,x=0,y=0,resize_source=False)
 shifted=add('ImageCompositeMasked',destination=shifted,source=b,x=256 if axis=='x' else 0,y=256 if axis=='y' else 0,resize_source=False)
 band=add('SolidMask',value=1.,width=256 if axis=='x' else 512,height=256 if axis=='y' else 512)
 band=add('FeatherMask',mask=band,left=80 if axis=='x' else 0,right=80 if axis=='x' else 0,top=80 if axis=='y' else 0,bottom=80 if axis=='y' else 0)
 mask=add('MaskComposite',destination=zero,source=band,x=128 if axis=='x' else 0,y=128 if axis=='y' else 0,operation='add')
 src=add('ImageCompositeMasked',destination=shifted,source=src,x=0,y=0,resize_source=False,mask=mask)
# Subtle albedo balance; this operates on the asset, never the review screenshots.
gain=add('SolidMask',value=.90,width=512,height=512)
src=add('ImageCompositeMasked',destination=blank,source=src,x=0,y=0,resize_source=False,mask=gain)
n=add('SaveImage',images=src,filename_prefix='fallout1_wall_crown_v4_20261115/cap-periodic')
h.execute(d,g,{n[0]:'cap-periodic.png'})
