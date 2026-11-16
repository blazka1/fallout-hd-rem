"""Generate six wall-compatible accent variants per theme in Qwen."""
import sys,uuid
from pathlib import Path
from PIL import Image
import pipeline as w
p=w.p;R=w.R;OUT=w.OUT
THEMES={
 'cavities':'Add ONE small deep irregular natural erosion cavity to the central rock face of each strip. It is a shallow visual recess in a solid wall, not a traversable entrance. Dark interior, rough fractured lip, varied lopsided shapes. No round drilled hole, doorway, bricks, masonry, daylight, or opening through the outer silhouette. Each cavity mouth about one third of the strip width, its height about one eighth of the strip height.',
 'cracks':'Add ONE distinctive broken fissure network to the central rock face of each strip: vary between a diagonal jagged fracture, a branching hairline seam, a short broad wedge crack, an offset split, a shallow fractured pocket and an irregular vertical fissure. Crisp brittle edges, subdued small highlights, dark recesses. Not glowing, painted, perfectly straight, oversized, or an architectural seam.',
 'moss':'Add a SMALL sparse patch of dark desaturated olive-brown cave moss anchored inside a central damp fracture or narrow rock ledge of each strip. Low compact irregular growth following the existing rock relief, some bare stone visible through it. About one third of strip width and one fifth of strip height. Keep the wall predominantly grey stone. Six different broken patch silhouettes. No bright green, lush vegetation, ferns, grass, vines, glow, floor plants, or carpet covering the wall.',
 'mushrooms':'The FOURTH image shows the EXISTING game mushroom species. Adapt those same muted grey-brown species to grow from crevices in the wall, not from the ground: TOP LEFT and TOP MIDDLE use 2 to 4 small broad irregular caps with short bent lateral stems; TOP RIGHT and BOTTOM LEFT use 2 to 4 small clustered irregular puffballs tucked into a rock pocket; BOTTOM MIDDLE and BOTTOM RIGHT use 2 to 4 slender drooping bell-shaped inkcap mushrooms with short curved stems emerging sideways from the rock. Preserve these species recognizable cap shapes, rough surfaces and restrained earthy palette. Small wall-attached colonies about half the strip width, about one fifth of its height, firmly connected to the CENTRAL lower rock face. No full ground clump, soil island, floating fungi, roots reaching the floor, luminous or red fantasy caps, large shelf fungus or new unrelated species.'}

def run(theme):
 d=OUT/'qwen/accents'/theme
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 plan=p.read(OUT/'plan.json');rows=[x for x in plan['new_variants'] if x['theme']==theme];assert len(rows)==6
 g={};outputs={};prefix='fallout1_wall_variety/accents/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 atlas=add('EmptyImage',width=960,height=1024,batch_size=1,color=0)
 alpha=add('SolidMask',value=1.,width=960,height=1024);atlas=add('JoinImageWithAlpha',image=atlas,alpha=alpha)
 layout=[]
 for i,row in enumerate(rows):
  path=OUT/'inputs/walls'/(row['source']+'.png');im=Image.open(path);width,height=im.size
  factor=min(240/width,464/height);dw,dh=round(width*factor),round(height*factor);x=i%3*320+(320-dw)//2;y=i//3*512+(512-dh)//2
  src=load(path);rgba=add('JoinImageWithAlpha',image=src,alpha=[src[0],1]);scaled=add('ImageScale',image=rgba,upscale_method='lanczos',width=dw,height=dh,crop='disabled')
  atlas=add('ImageCompositeMasked',destination=atlas,source=scaled,x=x,y=y,resize_source=False)
  layout.append(dict(**row,box=[x,y,dw,dh],native_hd=[width,height],input_sha256=p.sha(path)))
 saved=add('SaveImage',images=atlas,filename_prefix=prefix+'/input-atlas');outputs[saved[0]]='input-atlas.png'
 rock=load(R/'assets/generated/v13ent-cave-variety/style-match-v2-20261115/selected/geo-rock-07.png');rock=add('JoinImageWithAlpha',image=rock,alpha=[rock[0],1])
 context=load(OUT/'inputs/contexts/wall-01.png');context=add('ImageScale',image=context,upscale_method='lanczos',width=768,height=512,crop='disabled')
 prompt='''Edit ONLY the interiors of the SIX existing cave-wall slices in the FIRST image. Exact 3 columns by 2 rows, each cell 320 by 512. These are NARROW SLICES from a continuous isometric Fallout cave wall, NOT columns, pillars, standing stones, rock sculptures or separate objects. Keep every slice's exact width, height, position, contour, slope, top dark cut face, bottom edge and transparent surroundings. Preserve all six independently, no extra objects between cells, no labels or text. The SECOND image is the chosen cave rock MATERIAL reference, and the THIRD is the actual connected wall neighborhood for orientation. Match this neutral grey fractured stone with crisp laminar chips, deep irregular fissures and moderate contrast; the new detail must belong naturally in this material. Do not lighten the wall or change its palette.
Place the requested detail INSIDE THE CENTRAL 60 PERCENT OF EACH SLICE WIDTH, between 40 and 72 percent of its height. Leave the outer edges, roof/top and bottom completely unchanged, so it will still join the neighboring wall. Keep stone surrounding the detail. Six subtly different versions of the requested accent, small and restrained, no invented large structures. The first image layout and registration must remain exact.
'''+THEMES[theme]
 images={'images.image_1':atlas,'images.image_2':rock,'images.image_3':context}
 if theme=='mushrooms':
  board=add('EmptyImage',width=768,height=256,batch_size=1,color=0);blank=add('SolidMask',value=1.,width=768,height=256);board=add('JoinImageWithAlpha',image=board,alpha=blank)
  for i,name in enumerate(['cave-mushrooms.png','mushrooms-puffball.png','mushrooms-inkcap.png']):
   path=R/'assets/hd/v13ent/v14-campfire-x4/decor'/name;im=Image.open(path);f=min(224/im.width,224/im.height);ww,hh=round(im.width*f),round(im.height*f)
   src=load(path);rgba=add('JoinImageWithAlpha',image=src,alpha=[src[0],1]);scaled=add('ImageScale',image=rgba,upscale_method='lanczos',width=ww,height=hh,crop='disabled')
   board=add('ImageCompositeMasked',destination=board,source=scaled,x=i*256+(256-ww)//2,y=(256-hh)//2,resize_source=False)
  images['images.image_4']=board;saved=add('SaveImage',images=board,filename_prefix=prefix+'/existing-mushroom-reference');outputs[saved[0]]='existing-mushroom-reference.png'
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default');clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default');vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
 model=add('QwenImage21Cache',model=model,device='cpu',dtype='default');enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**images)
 sam=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15119500+list(THEMES).index(theme),steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 decoded=add('VAEDecode',samples=sam,vae=vae);saved=add('SaveImage',images=decoded,filename_prefix=prefix+'/'+theme);outputs[saved[0]]='raw.png'
 for a in layout:
  x,y,ww,hh=a['box'];crop=add('ImageCrop',image=decoded,x=x,y=y,width=ww,height=hh)
  saved=add('SaveImage',images=crop,filename_prefix=prefix+'/asset-%03d'%a['id']);outputs[saved[0]]='crops/asset-%03d.png'%a['id']
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.save(d/'layout.json',layout);p.execute(d,g,outputs)

if __name__=='__main__':
 for theme in THEMES:
  if len(sys.argv)==1 or sys.argv[1]==theme:run(theme)
