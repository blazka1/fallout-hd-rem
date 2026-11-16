from pathlib import Path
import importlib.util
from PIL import Image
R=Path(__file__).resolve().parents[2]
O=R/'assets/generated/v13ent-wall-geometry-kit/v3-edges-20261115'
spec=importlib.util.spec_from_file_location('wall_helpers',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.OUT=O
d=O/'edge-guard-comfy'
if (d/'run.json').exists():p.execute(d,{},{});raise SystemExit
width,height=Image.open(O/'edge-relief-imagegen.png').size
g={}
def add(t,**kw):n=str(len(g)+1);g[n]=p.node(t,**kw);return [n,0]
src=add('LoadImage',image=p.upload(O/'edge-relief-imagegen.png'))
flat=add('EmptyImage',width=width,height=height,batch_size=1,color=0x222222)
mask=add('SolidMask',value=1.,width=width,height=height-8)
soft=add('FeatherMask',mask=mask,left=0,top=40,right=0,bottom=0)
zero=add('SolidMask',value=0.,width=width,height=height)
guard=add('MaskComposite',destination=zero,source=soft,x=0,y=8,operation='add')
result=add('ImageCompositeMasked',destination=flat,source=src,x=0,y=0,resize_source=False,mask=guard)
original=add('LoadImage',image=p.upload(O.parent/'v2-registered-20261115/relief-atlas.png'))
top=add('SolidMask',value=1.,width=width,height=220)
top=add('FeatherMask',mask=top,left=0,top=0,right=0,bottom=72)
top=add('MaskComposite',destination=zero,source=top,x=0,y=0,operation='add')
result=add('ImageCompositeMasked',destination=original,source=result,x=0,y=0,resize_source=False,mask=top)
saved=add('SaveImage',images=result,filename_prefix='fallout1_wall_edges_v3_20261115/edge-relief-guarded')
p.execute(d,g,{saved[0]:'edge-relief-guarded.png'})
