"""ComfyUI-only connector experiment. Not a CE sprite export or install."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import kit
p=kit.p
O=kit.OUT
D=O/'connector-proof'
W,H=1536,512
def run():
 if (D/'run.json').exists():
  return p.execute(D,{}, {})
 g={};outputs={}
 def add(t,**kw):
  n=str(len(g)+1);g[n]=p.node(t,**kw);return [n,0]
 src={};sil={}
 for v in 'abc':
  im=add('LoadImage',image=p.upload(O/'imagegen/wall-01'/f'{v}.png'))
  src[v]=add('ImageCrop',image=im,x=0,y=0,width=W,height=H)
  m=add('ImageToMask',image=src[v],channel='red')
  sil[v]=add('ThresholdMask',mask=m,value=.04)
 common=sil['a']
 for v in 'bc':common=add('MaskComposite',destination=common,source=sil[v],x=0,y=0,operation='multiply')
 common=add('GrowMask',mask=common,expand=-32,tapered_corners=True)
 # Only an interior transition mask is softened; the rock image is never blurred.
 blurred=add('MaskToImage',mask=common)
 blurred=add('ImageBlur',image=blurred,blur_radius=16,sigma=6.)
 common=add('ImageToMask',image=blurred,channel='red')
 allowed=add('SolidMask',value=0.,width=W,height=H)
 for i in range(4):
  m=add('SolidMask',value=1.,width=384-96,height=H)
  m=add('FeatherMask',mask=m,left=20,top=0,right=20,bottom=0)
  allowed=add('MaskComposite',destination=allowed,source=m,x=i*384+48,y=0,operation='add')
 common=add('MaskComposite',destination=common,source=allowed,x=0,y=0,operation='multiply')
 # Each A/B/C candidate shares the new A outline and a 48-px connector collar.
 candidates={'a':src['a']}
 for v in 'bc':candidates[v]=add('ImageCompositeMasked',destination=src['a'],source=src[v],x=0,y=0,resize_source=False,mask=common)
 alpha=add('InvertMask',mask=sil['a'])
 for v in 'abc':
  rgba=add('JoinImageWithAlpha',image=candidates[v],alpha=alpha)
  n=add('SaveImage',images=rgba,filename_prefix='fallout1_wall_geometry_connector_proof/'+v)
  outputs[n[0]]=f'{v}.png'
  for i in range(4):
   tile=add('ImageCrop',image=rgba,x=i*384,y=0,width=384,height=H)
   n=add('SaveImage',images=tile,filename_prefix=f'fallout1_wall_geometry_connector_proof/{v}-{i}')
   outputs[n[0]]=f'blocks/{i}-{v}.png'
 m=add('MaskToImage',mask=common)
 n=add('SaveImage',images=m,filename_prefix='fallout1_wall_geometry_connector_proof/editable-mask')
 outputs[n[0]]='editable-mask.png'
 p.save(D/'contract.json',dict(status='technical concept only, not CE ready',size=[W,H],blocks=4,variants=3,block_width=384,connector_guard=48,canonical_outline='wall-01/a',rule='A original new geometry at every connector and outer outline; B/C relief confined to common interior',limit='Proves same-position variant seams only. Not arbitrary reordering, cross-context, game anchoring or all 62 FRMs. Interior transition can still look artificial.'))
 return p.execute(D,g,outputs)
if __name__=='__main__':run()
