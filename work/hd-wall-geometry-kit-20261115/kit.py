"""Geometry-first cave wall candidates; existing game remains untouched."""
from pathlib import Path
import sys,uuid,importlib.util,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry_helpers',R/'work/hd-cave-wall-variety-20261115/pipeline.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);p=w.p
OUT=R/'assets/generated/v13ent-wall-geometry-kit/v1-20261115';p.OUT=OUT
B=R/'build/hd-wall-geometry-kit-20261115';SRC=R/'assets/generated/v13ent-cave/v1-20261111/sources';PLAN=p.read(w.OUT/'plan.json')
STYLES={
 'a':'GEOMETRY A: broad blunt fractured buttresses, irregular massive angular rock volumes, uneven shallow steps. Thick supported shoulders, bevelled ledges. Vary spacing and size across each connected wall. Stay close to original wall plane.',
 'b':'GEOMETRY B: oblique overlapping large rock plates with varying thickness and angle, alternating recessed wedge-shaped shallow faces and solid projecting shoulders. Broad diagonal plane changes and broken asymmetric bevels, not repetitive vertical strips. Calm supported silhouette.',
 'c':'GEOMETRY C: alternating stout rock ribs and broad shallow concave recesses, uneven deeply fractured large masses with compact blunt feet. Recesses are solid dark planes, NOT holes through the wall. Varied relief rhythm with low protrusion and no narrow spikes.'}
def setup():
 if (OUT/'inventory.json').exists():return
 source={a['path']:a for a in p.read(SRC/'manifest.json')['assets']};rows=[];placements=[]
 for name,a in PLAN['walls'].items():
  s=source[name];stem=Path(name).stem
  rows.append(dict(source=name,stem=stem,id=a['asset_id'],native=[s['width'],s['height']],registration=s['registration'],instances=len(s['map_instances']),role='back/cutaway connector' if 53<=int(stem[2:])<=70 else 'visible face / corner / end',role_note='art-family inference'))
  Image.open(SRC/s['rgba_png']).save(OUT/'inputs'/(stem+'.png'))
  for o in s['map_instances']:
   if o['elevation']!=0 or o['flags']&1:continue
   u,v=199-o['tile']%200,o['tile']//200;ax,ay=48*(u//2)+32*(u&1)+16*v,-12*(u//2)+12*v
   x=ax+16+s['frm']['direction_x'][o['rotation']]+o['x']-s['width']//2;y=ay+8+s['frm']['direction_y'][o['rotation']]+o['y']-(s['height']-1)
   placements.append(dict(source=name,id=o['id'],tile=o['tile'],x=x,y=y,width=s['width'],height=s['height'],anchor_y=ay))
 placements.sort(key=lambda a:(a['anchor_y'],a['x'],a['id']))
 x0=min(a['x'] for a in placements);y0=min(a['y'] for a in placements);x1=max(a['x']+a['width'] for a in placements);y1=max(a['y']+a['height'] for a in placements)
 owners=np.zeros((y1-y0,x1-x0),np.int32);masks={n:np.array(Image.open(SRC/source[n]['rgba_png']).convert('RGBA'))[:,:,3]>0 for n in PLAN['walls']}
 for a in placements:
  view=owners[a['y']-y0:a['y']-y0+a['height'],a['x']-x0:a['x']-x0+a['width']];view[masks[a['source']]]=a['id']
 edges={};byid={a['id']:a for a in placements}
 for aa,bb in [(owners[:,:-1],owners[:,1:]),(owners[:-1],owners[1:])]:
  active=(aa>0)&(bb>0)&(aa!=bb);pairs=np.sort(np.stack([aa[active],bb[active]],axis=1),axis=1);unique,counts=np.unique(pairs,axis=0,return_counts=True)
  for ids,count in zip(unique,counts):
   key=tuple(map(int,ids));edges[key]=edges.get(key,0)+int(count)
 adjacency=[dict(objects=list(ids),sources=[byid[i]['source'] for i in ids],contact_pixels=count) for ids,count in edges.items() if count>=2]
 p.save(OUT/'inventory.json',dict(walls=rows,placements=placements,adjacency=adjacency,source_count=len(rows),instance_count=len(placements),planned_variants=3,geometry_scope='new internal rock volumes with original external attachment footprint; no runtime installation',adjacency_model='original masks, anchor-y painter approximation; not a CE occlusion guarantee'))
 p.save(OUT/'baseline.json',{str(f.relative_to(R)):p.sha(f) for f in [R/'AGENTS.md',R/'HD-TEXTURE-GUIDE.md',R/'runtime/hd-world-pilot/fallout-ce.exe',R/'runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json']})
 for c in PLAN['contexts']:
  Image.open(R/'assets/generated/v13ent-wall-joins/v1-20261112/prepared'/c['id']/'original-context.png').save(OUT/'inputs'/(c['id']+'.png'))
 print(f'Inventoried {len(rows)} sprites, {len(placements)} placements, {len(adjacency)} observed contacts',flush=True)
def generate(context,variant):
 d=OUT/'qwen-v3'/context/variant
 if (d/'run.json').exists():p.execute(d,{},{});return
 g={};outputs={};prefix='fallout1_geometry_kit/'+context+'-'+variant+'-'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return[k,0]
 src=add('LoadImage',image=p.upload(OUT/'inputs'/(context+'.png')))
 src=add('ImageScale',image=src,upscale_method='nearest-exact',width=1200,height=800,crop='disabled')
 canvas=add('EmptyImage',width=1216,height=800,batch_size=1,color=0);src=add('ImageCompositeMasked',destination=canvas,source=src,x=8,y=0,resize_source=False)
 prompt='Create a GEOMETRY BLOCKOUT REDESIGN of this connected classic Fallout 1 cave wall assembly for a 2D isometric sprite engine. Use the provided scene as an exact footprint and perspective blueprint. Keep the orthographic isometric camera, overall wall heights, thickness, top cut boundaries, bends, endpoints, bottom contact lines, black gaps and exact placement of every connected wall segment. Do not move, rotate, resize or disconnect wall assemblies. Redesign INTERNAL ROCK VOLUMES and large-scale relief clearly and substantially: fresh varied geometry, not sharper textures. Preserve grounded rugged Fallout cave character, thick structurally supported stone, restrained natural angular shapes. Adjacent pieces must look like one continuous rock mass with shared strata and compatible junctions. No narrow tile columns or periodic repeats. Protrusions stay within the wall footprint, never filling black floor gaps. No new entrances, tunnels, through-holes, spikes, teeth, fingers, unsupported shelves, free-standing rocks, masonry, bricks, plants or mushrooms. Render all walls as clean MATTE NEUTRAL GREY untextured hard rock with consistent upper-left illumination and broad readable planar shading: a geometry study for a pre-rendered 1997 Fallout background. Hard chipped planes and angular bevels, NOT rounded soft clay. Absolutely no tiny cracks, grain, photographic texture, noise, speckles or fine scratches: geometry and volume alone. Keep empty space uniformly BLACK. All wall groups use the same medium-dark grey material and light. No captions or guides. '+STYLES[variant]
 prompt=prompt.replace('as an exact footprint and perspective blueprint','as a placement and perspective blueprint').replace('overall wall heights, thickness, top cut boundaries, bends, endpoints, bottom contact lines','overall wall heights, thickness, bends, shared endpoints and bottom contact anchors')
 prompt+=' CRITICAL GEOMETRY CORRECTION: the original thin hanging stalactite fingers, long downward corner teeth, projecting snout shapes and ragged top spikes are REJECTED. Remove them completely. Replace those local outlines with continuous blunt bevelled rock shoulders and broad supported facets. Do NOT preserve these old protrusions in the name of matching the blueprint. The shared attachment points and ground contact stay fixed, but the exposed contour and rock face profile must be redesigned. Use only a few LARGE well-defined irregular stone masses per long stretch, not hundreds of small faceted pebbles. Different masses are joined by shallow broad natural creases, not tiny noisy cracks. This is a restrained substantial geometry redesign with clean readable large planes.'
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default');clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default');vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors');model=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 master=add('LoadImage',image=p.upload(OUT/'geometry-master.png'))
 master=add('ImageScale',image=master,upscale_method='lanczos',width=768,height=512,crop='disabled')
 prompt+=' IMAGE 2 IS THE USER-APPROVED NEW GEOMETRY MASTER. Follow its broad, clean, blunt supported rock volumes and simplicity closely. Use row '+{'a':'TOP','b':'MIDDLE','c':'BOTTOM'}[variant]+' of image 2 as the geometry treatment. Image 1 supplies ONLY camera, footprint and placement. Do NOT copy its old internal grooves, cluttered small rocks, old teeth or tiny stone masses. The geometry style must clearly match image 2, adapted continuously to each wall assembly in image 1.'
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':src,'images.image_2':master})
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15160000+int(context[-2:])*10+ord(variant)-97,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 raw=add('VAEDecode',samples=sample,vae=vae);node=add('SaveImage',images=raw,filename_prefix=prefix+'/raw');outputs[node[0]]='raw.png'
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.execute(d,g,outputs)
if __name__=='__main__':
 setup()
 if len(sys.argv)>1 and sys.argv[1]=='generate':generate(sys.argv[2],sys.argv[3])
