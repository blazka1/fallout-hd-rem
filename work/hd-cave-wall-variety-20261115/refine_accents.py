"""Individual controlled repairs for partial walls and wall-attached fungi."""
import sys,uuid
from PIL import Image
import pipeline as w
p=w.p;OUT=w.OUT;R=w.R

def run(id):
 d=OUT/'qwen/accents-refined'/('asset-%03d'%id)
 if (d/'result.json').exists():return
 if (d/'run.json').exists():p.execute(d,{},{});return
 plan=p.read(OUT/'plan.json');a=next(x for x in plan['new_variants'] if x['id']==id)
 c=next(c for c in plan['contexts'] if any(s['source']=='art/walls/'+a['source']+'.frm' for s in c['selected']))
 path=OUT/'prepared/material-v2'/c['id']/'assets'/('asset-%03d.png'%a['base'])
 im=Image.open(path);dw=round(im.width*960/im.height);dh=960;x=(384-dw)//2;y=32
 g={};outputs={};prefix='fallout1_wall_variety/refined/'+uuid.uuid4().hex
 def add(kind,**kw):k=str(len(g)+1);g[k]=p.node(kind,**kw);return [k,0]
 def load(path):return add('LoadImage',image=p.upload(path))
 base=load(path);base=add('JoinImageWithAlpha',image=base,alpha=[base[0],1]);base=add('ImageScale',image=base,upscale_method='lanczos',width=dw,height=dh,crop='disabled')
 canvas=add('EmptyImage',width=384,height=1024,batch_size=1,color=0);mask=add('SolidMask',value=1.,width=384,height=1024);canvas=add('JoinImageWithAlpha',image=canvas,alpha=mask)
 canvas=add('ImageCompositeMasked',destination=canvas,source=base,x=x,y=y,resize_source=False)
 save=add('SaveImage',images=canvas,filename_prefix=prefix+'/input');outputs[save[0]]='input.png'
 if id==193:
  detail='Add ONE small sparse irregular patch of dark desaturated olive-brown cave moss on the solid LOWER rock face, immediately BELOW the existing central black crevice at 72 percent of wall height. Keep the existing central dark crevice itself unchanged. Thin granular low moss growth following stone fissures, broken edges and small bare areas between tufts, total width 40 percent of wall width and height 12 percent of wall height. Not a solid slab, rectangular carpet, leaf, vines or bright green foliage. Keep the exact rock texture around it.'
  refs={}
 elif id==183:
  detail='Add ONE small irregular dark erosion cavity in the BROAD LOWER ROCK FACE at 74 percent of the wall height, horizontally centered on that broad lower rock mass. The empty cutout ABOVE the lower rock is NOT the requested cavity. Carve a small recessed black pocket with a chipped jagged stone lip into the solid lower face. Mouth width 35 percent of wall width, height 9 percent of wall height. Keep solid stone around it. No doorway, tunnel, round drilled hole or change to the silhouette.'
  refs={}
 else:
  ids=[x['id'] for x in plan['new_variants'] if x['theme']=='mushrooms'];i=ids.index(id)
  species=['cave-mushrooms.png','mushrooms-puffball.png','mushrooms-inkcap.png'][i//2]
  ref=load(R/'assets/hd/v13ent/v14-campfire-x4/decor'/species);ref=add('JoinImageWithAlpha',image=ref,alpha=[ref[0],1]);refs={'images.image_2':ref}
  kind=['broad irregular grey-brown caps and SHORT curved side-attached stalks','small irregular round grey-brown puffballs, firmly embedded in a rock pocket','small drooping pointed bell caps with SHORT curved side-attached stems'][i//2]
  detail=f'Add exactly ONE compact colony of 2 or 3 small mushrooms of the SAME SPECIES shown in image 2: {kind}. Image 2 is the previously approved floor mushroom reference; adapt it to growth from a wall crevice. All caps and stems grow together from ONE attachment point on a narrow central rock ledge at 68 percent of the wall height. The ENTIRE colony lies inside the middle 50 percent of the visible wall width, with plenty of bare rock on BOTH sides. Total colony width 45 percent of the wall width, height 13 percent of wall height. No mushrooms near the outer edges or bottom, no other colonies, no stems reaching the ground, no long dangling stems, no cut-off caps, no floating mushrooms, no glow, no red colors. Restrained muted grey-brown palette matching the reference.'
  if a['source']=='ca032':detail+=' The wall has an empty central cutout. Place the colony on the solid BROAD LOWER ROCK MASS, at 72 percent of wall height, not in that empty cutout.'
 prompt='Image 1 is ONE existing narrow isometric Fallout cave WALL SLICE, with a transparent background, NOT a pillar or separate standing stone. Keep its exact framing, position, silhouette, dimensions, large rock geometry, neutral dark grey fractured rock material, lighting, dark top cut and every edge. Change ONLY a SMALL interior detail in the lower-middle of the solid visible rock face. Preserve the surrounding texture exactly. Do not redraw, enlarge, straighten, smooth, lighten or recolor the wall. '+detail
 model=add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default');clip=add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default');vae=add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
 model=add('QwenImage21Cache',model=model,device='cpu',dtype='default');enc=add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':canvas,**refs})
 sample=add('KSampler',model=model,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=15119800+id,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
 decoded=add('VAEDecode',samples=sample,vae=vae);save=add('SaveImage',images=decoded,filename_prefix=prefix+'/raw');outputs[save[0]]='raw.png'
 crop=add('ImageCrop',image=decoded,x=x,y=y,width=dw,height=dh);save=add('SaveImage',images=crop,filename_prefix=prefix+'/crop');outputs[save[0]]='crop.png'
 d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8');p.save(d/'registration.json',dict(asset=id,input=str(path.relative_to(R)),crop=[x,y,dw,dh]));p.execute(d,g,outputs)

if __name__=='__main__':
 for id in ([int(x) for x in sys.argv[1:]] or [183,178,182,186,190,194,198]):run(id)
