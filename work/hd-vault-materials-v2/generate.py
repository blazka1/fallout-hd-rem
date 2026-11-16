"""Resumable Qwen edits for clean interior, rusty exterior, and all door poses."""
from pathlib import Path
import importlib.util,json,uuid,argparse,urllib.parse
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('q',ROOT/'work/hd-terminal-indicator/qwen-terminal.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
h=q.h;BASE=q.BASE
RUN=ROOT/'assets/generated/v13ent-vault/materials-v2-20261114'
OLD=ROOT/'assets/generated/v13ent-vault/v1-rust-20261112'
PROMPTS={
'floor':'''Refine this exact Fallout vault interior floor tile: a metal rectangular grating seen in the same isometric projection. Lock every bar, edge, border, opening and the exact tile outline. Restore clean maintained dark grey steel and crisp machined edges, subtle satin metal grain, restrained highlights and dark gaps between bars. Remove orange rust and dirty blotches. No corrosion, peeling, new bars, added objects or glow. Keep subdued original lighting and late-1990s prerendered Fallout style. Material detail only, no geometry changes. The tile must still repeat seamlessly with itself.''',
'walls':'''Refine this exact isometric Fallout vault interior wall assembly, preserving every panel seam, vent, corner, perspective and silhouette in exactly the same position. These are maintained INSIDE walls of an occupied underground vault: restore clean satin steel and pale desaturated grey-green painted metal, intact paint, precise machined bevels, clean dark panel gaps, readable vent slats, subtle fine brushed-metal grain and tiny signs of normal use. Absolutely no orange rust, corrosion, peeling paint, dirt crust or cracked concrete. Sharper functional material details, no blur, no soft smudges, no added seams or random greebles. Keep subdued original lighting and 1990s prerendered Fallout style. Preserve the two separate wall strips and empty background exactly, no floor or new objects. Geometry is locked; edit materials only.''',
'frame':'''Refine this exact isometric Fallout vault outer door-frame sprite. Lock the framing, perspective, all outer and inner boundaries, cable, metal sill, rivets and plates in their exact positions. Keep the repaired solid metal panel at the lower left beneath the curved cable: do not cut a terminal-shaped hole in it and do not add a terminal. This EXTERIOR frame is exposed to cave moisture: retain dark steel, convincing orange-brown rust, chipped paint and pitted metal, with crisp selective edges, clear bolts and fine metal scratches. Improve the small lower-left panel and sill particularly: remove blurry smeared materials, replace them with sharp coherent metal texture matching the rest. No halo, bright outlines, green checkerboard or dark terminal-shaped stain. Keep the same restrained lighting and shape. Do not add objects or new geometry. Empty opening and background remain empty.''',
'door':'''Precisely refine this complete 5-column by 3-row sprite atlas of FIFTEEN consecutive poses of the SAME Fallout 13 vault door. Keep all fifteen cells, their exact placement, perspective, silhouette, rotation and scale. Do not add or remove or reorder cells. The exterior door must remain rusty: detailed dark steel, chipped paint, restrained orange-brown rust deposits, readable hard edges, scratches, machined teeth and the original number 13. Improve material clarity, remove smudgy blurry surfaces. Material and lighting must be consistent across every animation pose; keep all stationary panels and sill identical across the sequence. This is a material restoration, no redesign or added shapes, no extra numbers, no glowing outline, no bloom. Preserve empty cell backgrounds and precise sprite registration.'''}
def save(out,name,v):(out/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit(kind):
 out=RUN/kind;out.mkdir(parents=True,exist_ok=True)
 if (out/'run.json').exists():raise RuntimeError('Saved run exists: collect')
 h.require_idle(BASE)
 models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
 schemas,checks=h.preflight(BASE,models);assert checks['ready_to_submit']
 g={};outputs={};prefix='fallout1_vault_materials/'+kind+'-'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(BASE,p,'vault-material-'+uuid.uuid4().hex+'.png'))
 if kind=='door':
  canvas=add('EmptyImage',width=1938,height=974,batch_size=1,color=0)
  slots=json.loads((OLD/'atlas-input/run.json').read_text())['slots']
  for slot in slots:
   im=load(ROOT/f"assets/hd/v13ent/v14-campfire-x4/art/scenery/v13secr2.frm/frames/d0-f{slot['frame']:03}.png")
   rgb=add('ImageScale',image=im,upscale_method='area',width=378,height=314,crop='disabled')
   alpha=add('InvertMask',mask=[im[0],1]);alpha=add('MaskToImage',mask=alpha)
   alpha=add('ImageScale',image=alpha,upscale_method='nearest-exact',width=378,height=314,crop='disabled');alpha=add('ImageToMask',image=alpha,channel='red')
   canvas=add('ImageCompositeMasked',destination=canvas,source=rgb,x=slot['atlas_rect'][0],y=slot['atlas_rect'][1],resize_source=False,mask=alpha)
  size=[1536,768]
 else:
  source={'walls':OLD/'wall-input-atlas/metal-wall-context.png','frame':ROOT/'assets/hd/v13ent/terminal-recess-v4/vault-frame.png','floor':ROOT/'assets/hd/v13ent/v14-campfire-x4/art/tiles/grt2000.frm.png'}[kind]
  canvas=load(source);size={'walls':[1152,832],'frame':[1152,768],'floor':[512,256]}[kind]
 ref=add('ImageScale',image=canvas,upscale_method='lanczos',width=size[0],height=size[1],crop='disabled')
 k=add('SaveImage',images=ref,filename_prefix=prefix+'/reference');outputs[k[0]]='reference.png'
 unet=add('UNETLoader',unet_name=models['unet'],weight_dtype='default');clip=add('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default');vae=add('VAELoader',vae_name=models['vae'])
 cache=add('QwenImage21Cache',model=unet,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=PROMPTS[kind],negative_prompt='',vae=vae,resolution=0,**{'images.image_1':ref})
 sam=add('KSampler',model=cache,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=1411202610+['walls','frame','door','floor'].index(kind),steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
 im=add('VAEDecode',samples=sam,vae=vae);k=add('SaveImage',images=im,filename_prefix=prefix+'/raw');outputs[k[0]]='raw.png'
 wf=h.make_workflow(g,schemas);save(out,'workflow.json',wf);save(out,'prompt-api.json',g);save(out,'outputs.json',outputs);save(out,'preflight.json',checks)
 (out/'prompt.txt').write_text(PROMPTS[kind],encoding='utf-8')
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save(out,'run.json',run);print(json.dumps(run))
def collect(kind):
 out=RUN/kind;pid=json.loads((out/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save(out,'history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in json.loads((out/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(out/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected '+kind)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);p.add_argument('kind',choices=list(PROMPTS));a=p.parse_args();{'submit':submit,'collect':collect}[a.action](a.kind)
