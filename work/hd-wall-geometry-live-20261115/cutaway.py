"""Native ComfyUI geometry-blockout cap preparation; exact original tile alpha."""
from pathlib import Path
import sys,importlib.util,json
from PIL import Image
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from bake import decode,pack,O,D
spec=importlib.util.spec_from_file_location('wall_helpers',R/'work/cave-variety-seed-qwen-20261115/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.OUT=O
def main():
 d=O/'cutaway';d.mkdir(exist_ok=True)
 if (d/'run.json').exists():p.execute(d,{},{});return
 g={};out={}
 def add(t,**kw):n=str(len(g)+1);g[n]=p.node(t,**kw);return [n,0]
 for id in [62,63]:
  for name in [f'asset-{id:03}']+[f'tile-{id:03}-v{v}' for v in range(1,4)]:
   a=decode(D/f'{name}.rgba');path=d/(name+'-source.png');Image.fromarray(a).save(path)
   old=add('LoadImage',image=p.upload(path));flat=add('EmptyImage',width=a.shape[1],height=a.shape[0],batch_size=1,color=0x222222)
   rgba=add('JoinImageWithAlpha',image=flat,alpha=[old[0],1]);n=add('SaveImage',images=rgba,filename_prefix='fallout1_wall_geometry_cutaway/'+name)
   out[n[0]]=name+'.png'
 p.execute(d,g,out)
if __name__=='__main__':main()
