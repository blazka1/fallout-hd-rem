"""Comfy-native color matching, lossless package and unchanged assignment map."""
import sys,json,struct,uuid,shutil,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'work/cave-variety-seed-qwen-20261115'))
import pipeline as p
OLD=p.OUT;p.OUT=R/'assets/generated/v13ent-cave-variety/style-match-v2-20261115'
from qa import GROUPS
PACK=R/'assets/hd/v13ent/cave-distribution-v2'

def prepare():
 n=p.node
 for gi,(group,sources) in enumerate(GROUPS):
  src=p.OUT/'qwen'/group;dst=p.OUT/'prepared'/group
  if not (src/'result.json').exists():raise RuntimeError('Generation incomplete: '+group)
  if (dst/'result.json').exists():continue
  if (dst/'run.json').exists():p.execute(dst,{},{});continue
  g={};outputs={};info=[];prefix='fallout1_cave_style_v2/matched/'+uuid.uuid4().hex
  for i,stem in enumerate(sources):
   name='geo-formation-%02d'%(i+1) if gi==3 else 'geo-rock-%02d'%(gi*4+i+1)
   original=OLD/'sources/art/scenery'/(stem+'.frm.current.png');source=src/'sprites'/(name+'.png')
   old=np.array(Image.open(original).convert('RGBA'));raw=np.array(Image.open(source).convert('RGBA'))
   target=old[:,:,:3][old[:,:,3]>200].mean(0);actual=raw[:,:,:3][raw[:,:,3]>200].mean(0)
   gain=target/actual
   assert min(gain)>.5 and max(gain)<1.5,(name,gain.tolist())
   # Multiply darker channels, or screen a small neutral lift when a generated
   # column is darker than its reference. Both remain native Comfy operations.
   lift=np.rint(np.clip((target-actual)/(255-actual),0,1)*255).astype(int)
   rgb=np.rint(np.clip(gain,0,1)*255).astype(int);color=int(rgb[0]*65536+rgb[1]*256+rgb[2]);base=i*8
   def key(x):return str(base+x)
   g[key(1)]=n('LoadImage',image=p.upload(source))
   g[key(2)]=n('EmptyImage',width=512,height=512,batch_size=1,color=color)
   g[key(3)]=n('ImageBlend',image1=[key(1),0],image2=[key(2),0],blend_factor=1.,blend_mode='multiply')
   g[key(4)]=n('EmptyImage',width=512,height=512,batch_size=1,color=int(lift[0]*65536+lift[1]*256+lift[2]))
   g[key(5)]=n('ImageBlend',image1=[key(3),0],image2=[key(4),0],blend_factor=1.,blend_mode='screen')
   g[key(6)]=n('JoinImageWithAlpha',image=[key(5),0],alpha=[key(1),1])
   g[key(7)]=n('SaveImage',images=[key(6),0],filename_prefix=prefix+'/'+name)
   outputs[key(7)]=name+'.png'
   info.append(dict(id=name,source_sha256=p.sha(source),reference=str(original.relative_to(R)),reference_sha256=p.sha(original),target_mean_rgb=target.tolist(),raw_mean_rgb=actual.tolist(),gain=(rgb/255).tolist(),screen_lift=(lift/255).tolist(),method='Comfy ImageBlend per-channel multiply/screen; native generated alpha restored; no procedural texture or sharpening'))
  p.save(dst/'color-match.json',info);p.execute(dst,g,outputs)
 selected=p.OUT/'selected';selected.mkdir(exist_ok=True)
 for group,_ in GROUPS:
  for path in (p.OUT/'prepared'/group).glob('geo-*.png'):shutil.copy2(path,selected/path.name)

def package():
 PACK.mkdir(parents=True,exist_ok=True)
 dist=p.read(R/'assets/hd/v13ent/cave-distribution-v1/distribution.json')
 records=[]
 for name,a in dist['assets'].items():
  path=p.OUT/'selected'/(name+'.png');im=Image.open(path).convert('RGBA');arr=np.array(im);assert im.size==(512,512)
  strong=arr[:,:,3]>127
  assert not any([strong[0].any(),strong[-1].any(),strong[:,0].any(),strong[:,-1].any()]),name
  box=Image.fromarray(((arr[:,:,3]>8)*255).astype('uint8')).getbbox();x,y,u,v=box
  a['box']=[max(0,x-4),max(0,y-4),min(512,u+4),min(512,v+4)]
  a['source']=str(path.relative_to(R));a['sha256']=p.sha(path)
  (PACK/a['file']).write_bytes(struct.pack('<4sIIII',b'F1HD',1,512,512,4)+im.tobytes())
  records.append(dict(id=name,asset_id=a['id'],source=a['source'],source_sha256=a['sha256'],rgba_sha256=p.sha(PACK/a['file']),alpha_border_pixels=0))
 rows=[]
 for item in sorted((x for x in dist['assignments'] if x['new']),key=lambda x:x['index']):
  o=item['object'];a=dist['assets'][item['appearance']];x,y,u,v=a['box'];sw,sh=u-x,v-y
  scale=(o['height']-2)/sh if item['group']=='columns' else min((o['width']-4)/sw,(o['height']-2)/sh)
  dw,dh=max(1,round(sw*scale)),max(1,round(sh*scale));dx=(o['width']-dw)//2;dy=o['height']-dh
  item.update(source_box=[x,y,sw,sh],draw_in_classic_rect=[dx,dy,dw,dh],aspect_ratio_error=abs(dw/dh-sw/sh),bounds_expand=dx<0 or dy<0 or dx+dw>o['width'] or dy+dh>o['height'])
  vals=[item['index'],o['id'],o['fid'],o['pid'],o['tile'],o['elevation'],o['x'],o['y'],o['rotation'],a['id'],o['width'],o['height'],x,y,sw,sh,dx,dy,dw,dh]
  rows.append(' '.join(map(str,vals)))
 assert len(records)==16 and len(rows)==76
 oldpack=R/'assets/hd/v13ent/cave-distribution-v1'
 shutil.copy2(oldpack/'cave-variety-assets.tsv',PACK/'cave-variety-assets.tsv')
 (PACK/'cave-variety-placements.tsv').write_text('# unchanged object identities, revised source crops / uniform-fit draw rectangles\n'+'\n'.join(rows)+'\n',encoding='utf-8')
 dist['style_revision']='v2: current HD reference material, matched neutral grey; moderate natural silhouettes'
 p.save(PACK/'distribution.json',dist);p.save(PACK/'manifest.json',dict(status='prepared for in-engine validation',records=records,placements=76,old_appearances=40,new_appearances=76,executable_modified=False))
 print('PACKAGED',PACK,flush=True)

if __name__=='__main__':prepare();package()
