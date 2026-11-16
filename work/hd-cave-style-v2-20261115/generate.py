"""Reference-led correction of the overly smooth/fantastic cave candidates."""
import sys, uuid
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/cave-variety-seed-qwen-20261115'))
import pipeline as p
OLD=p.OUT
p.OUT=ROOT/'assets/generated/v13ent-cave-variety/style-match-v2-20261115'
GROUPS=[
 ('rocks-01',['rock01','rock02','rock03','rock04'],[
  'A low asymmetric heap of four broken stratified rocks, one large horizontal block and three smaller close-set fragments. NOT a stair or stacked flat plates.',
  'A compact triangular heap of three thick chunky broken boulders, taller at the left; blunt fractured top, no thin pointed fin.',
  'Two touching unequal squat boulders with an irregular dark fissure between them and a few small chips at the base; no isolated upright pillars.',
  'A broad low angular boulder with two attached fractured chunks at its lower right, firmly resting on the ground; no undercut feet or hollow underneath.']),
 ('rocks-02',['rock05','rock06','rock01','rock03'],[
  'A low dense pile of five rough broken rocks in an irregular oval footprint, completely natural random rubble; no arch, bridge or deliberate opening.',
  'Three thick eroded rock blocks pressed closely together, one moderately taller at the back; blunt fractured tops, no thin fins, blades or needles.',
  'A broad irregular boulder broken into three close-set uneven angular parts, rough strata and chipped contours; not a smooth split sphere.',
  'An asymmetric outcrop of four thick fractured strata tilted in different directions with small rubble touching the base; no regular stairs.']),
 ('rocks-03',['rock04','rock05','rock06','rock02'],[
  'A dense asymmetric cluster of six unequal angular rocks with overlapping masses, larger at the back-left and small at front-right; no ring, horseshoe or central hole.',
  'A compact triangular mound of three stout broken boulders with uneven blunt tops, one a little taller at center; no tall pinnacle or sharp trident.',
  'A squat fractured oblong boulder lying diagonally, with a second smaller jagged piece directly beside it, coarse layered stone; no regular polygonal column.',
  'Two broad irregular broken blocks resting firmly against each other, one tilted only slightly, grounded with rubble at the base; no unsupported sheet or sail.']),
 ('formations',['cstalag1','cstalag2','cvcolum1','cvcolum2'],[
  'A grounded cluster of three unequal natural tapered stalagmites, moderately tall main cone off-center and two short thick companions, irregular fluted mineral deposits; no needles.',
  'One slightly crooked thick natural stalagmite narrowing to a single blunt pointed tip with two very short mineral lumps near its base; no Y branches or fork.',
  'One near-vertical natural cave column, mildly asymmetric thick trunk, flared irregular foot, a broad flat dark roof-contact cut at the top just like the reference; no thin curved waist.',
  'One thick natural cave column with a shallow vertical fissure and two joined lower lobes, continuous solid upper body and dark roof-contact cut; no window or arch.'])]

def run(group):
 name,sources,descriptions=group;d=p.OUT/'qwen'/name
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 n=p.node;g={};outputs={};num=0
 def add(kind,**kw):
  nonlocal num
  num+=1;g[str(num)]=n(kind,**kw);return [str(num),0]
 blank=add('EmptyImage',width=1024,height=1024,batch_size=1,color=0)
 transparent=add('SolidMask',value=1.,width=1024,height=1024)
 atlas=add('JoinImageWithAlpha',image=blank,alpha=transparent)
 provenance=[]
 for i,stem in enumerate(sources):
  path=OLD/'sources/art/scenery'/(stem+'.frm.current.png')
  im=Image.open(path);w,h=im.size;factor=min(416/w,416/h);dw,dh=round(w*factor),round(h*factor)
  loaded=add('LoadImage',image=p.upload(path));joined=add('JoinImageWithAlpha',image=loaded,alpha=[loaded[0],1])
  scaled=add('ImageScale',image=joined,upscale_method='lanczos',width=dw,height=dh,crop='disabled')
  atlas=add('ImageCompositeMasked',destination=atlas,source=scaled,x=i%2*512+(512-dw)//2,y=i//2*512+460-dh,resize_source=False)
  provenance.append(dict(file=str(path.relative_to(ROOT)),sha256=p.sha(path)))
 prefix='fallout1_cave_style_v2/'+uuid.uuid4().hex
 saved=add('SaveImage',images=atlas,filename_prefix=prefix+'/reference-layout');outputs[saved[0]]='reference-layout.png'
 reference='formations' if name=='formations' else ('rocks-b' if name=='rocks-02' else 'rocks-a')
 seed=OLD/'seedvr2-current'/reference/'seedvr2-x4.png'
 load=add('LoadImage',image=p.upload(seed));seedref=add('JoinImageWithAlpha',image=load,alpha=[load[0],1])
 prompt='''Edit the FIRST image into four believable VARIANTS of these same classic Fallout 1 cave sprites, in the SAME 2 by 2 layout. Image 1 is the PRIMARY material, rendering-style and camera reference. Image 2 is the SeedVR2 restoration of the same rock family, a secondary reference. Match the PRIMARY reference's densely fractured, sharply stratified grey rock texture and pre-rendered isometric appearance extremely closely. The previous attempt failed because it was smooth, soft low-poly clay with extravagant fantasy silhouettes. Correct that failure.
RENDERING: hard mineral surfaces, pronounced irregular overlapping laminar fractures, many medium-sized chipped edges, small angular plates and pits within larger stone masses. Deep dark crevices between irregular blocks, restrained crisp pale-grey edge accents lit from upper left, warm-neutral charcoal shadow. Rich original-style texture visibly covering ALL large faces, irregular relief at coarse and medium scales. Edges should look brittle and freshly chipped, not polished, rounded, inflated or rubbery. Preserve the reference contrast and neutral grey brightness. No blanket smooth planes, no low-poly shading, no soft clay, no bevelled toy rocks, no blue or white stone, no uniform noise or over-sharpening halos.
GEOMETRY: modest natural changes of mass arrangement and contour, roughly 20 to 30 percent variation from the reference family, enough to avoid identical repeats. Keep rocks chunky, heavy, grounded and geologically ordinary. No fantasy architecture, perfect arches, holes, thin sails, huge needles, floating slabs, regular stairs, circular arrangements or Y-shaped trunks. Every shape must belong naturally among the ORIGINAL reference sprites, not look like a showcase sculpt.
Each cell is 512x512. Keep each entire object within its cell with at least 30 pixels clear margin, same bottom-contact height and same orthographic isometric camera. Four separate objects only, no overlap between cells, real transparent RGBA background and transparent space around every sprite. No ground plane or full ground shadow, text, border, labels, scenery, characters or invented light source.
'''
 for pos,desc in zip(['TOP LEFT','TOP RIGHT','BOTTOM LEFT','BOTTOM RIGHT'],descriptions):prompt+=pos+': '+desc+'\n'
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
 clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
 vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
 cached=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 encoded=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':atlas,'images.image_2':seedref})
 sampled=add('KSampler',model=cached,positive=encoded,negative=[encoded[0],1],latent_image=[encoded[0],2],seed=15118001+[x[0] for x in GROUPS].index(name),steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 decoded=add('VAEDecode',samples=sampled,vae=vae)
 saved=add('SaveImage',images=decoded,filename_prefix=prefix+'/raw');outputs[saved[0]]='raw.png'
 for i in range(4):
  identifier='geo-formation-%02d'%(i+1) if name=='formations' else 'geo-rock-%02d'%([x[0] for x in GROUPS].index(name)*4+i+1)
  crop=add('ImageCrop',image=decoded,x=i%2*512,y=i//2*512,width=512,height=512)
  saved=add('SaveImage',images=crop,filename_prefix=prefix+'/'+identifier);outputs[saved[0]]='sprites/'+identifier+'.png'
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
 p.save(d/'provenance.json',dict(primary=provenance,secondary=dict(file=str(seed.relative_to(ROOT)),sha256=p.sha(seed)),request='match original/updated texture more strongly; calmer natural geometry',runtime_modified=False))
 p.execute(d,g,outputs)

if __name__=='__main__':
 for group in GROUPS:
  if len(sys.argv)==1 or sys.argv[1]==group[0]:run(group)
