"""Qwen clean steel donor, then exact masked registration in ComfyUI."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse,shutil
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
ROOT=z.ROOT;h=z.h;BASE=z.BASE
OUT=ROOT/'assets/generated/v13ent-vault/smooth-trim-v4-20261114'
SOURCE=ROOT/'assets/hd/v13ent/vault-clean-trim-v3/asset-016.png'
MASK=ROOT/'assets/generated/v13ent-vault/clean-trim-v3-20261114/complete/edit-mask.png'
PROMPT='''Image 1 is the exact isometric Fallout vault doorway frame to restore. Image 2 is a material reference ONLY: the maintained smooth metal walls inside the vault. Preserve image 1 framing, every silhouette, shape, panel seam, bevel, plate, cable, opening and perspective in exactly the same position. Restore the silver-grey rear-facing surfaces of image 1 to smooth maintained satin metal like image 2: especially the tall narrow LEFT SIDE FACE and the thin raised BACK UPPER RIM with its two triangular end caps. Completely remove flaking paint, raised peeling crust, corrosion blisters, craters, pitting, rust patches and cracked plaster texture from these silver surfaces. Replace those defects with intact flat metal, restrained fine satin grain, very subtle clean brushed-metal detail, crisp seams and consistent smooth shading. Preserve the current neutral silver-grey tone and brightness of these surfaces. Do not simply desaturate the corrosion or blur it. The large dark brown outward-facing front and upper frame plates remain rusty. No new seams, vents, objects, symbols, highlights, bloom, warping or changed outline. Do not paste image 2 into the scene. Same subdued late-1990s prerendered Fallout aesthetic, identical geometry and lighting. Empty background and central opening stay empty.'''
def save(out,n,v):z.save(out,n,v)
def submit():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'run.json').exists();h.require_idle(BASE)
 models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
 schemas,checks=h.preflight(BASE,models);assert checks['ready_to_submit']
 g={};outputs={};prefix='fallout1_smooth_trim/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(BASE,p,'smooth-trim-'+uuid.uuid4().hex+'.png'))
 src=load(SOURCE);ref=add('ImageScale',image=src,upscale_method='lanczos',width=1024,height=672,crop='disabled')
 material=load(ROOT/'assets/hd/v13ent/vault-materials-v2/asset-152.png');material=add('ImageScale',image=material,upscale_method='lanczos',width=96,height=512,crop='disabled')
 model=add('UNETLoader',unet_name=models['unet'],weight_dtype='default');clip=add('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default');vae=add('VAELoader',vae_name=models['vae'])
 cache=add('QwenImage21Cache',model=model,device='cpu',dtype='default')
 enc=add('TextEncodeQwenImage21',clip=clip,prompt=PROMPT,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':ref,'images.image_2':material})
 sam=add('KSampler',model=cache,positive=enc,negative=[enc[0],1],latent_image=[enc[0],2],seed=1411202641,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0)
 im=add('VAEDecode',samples=sam,vae=vae)
 for image,name in [(ref,'reference'),(im,'raw')]:
  k=add('SaveImage',images=image,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
 wf=h.make_workflow(g,schemas)
 for n,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs),('preflight.json',checks)]:save(OUT,n,v)
 (OUT/'prompt.txt').write_text(PROMPT,encoding='utf-8');shutil.copy2(SOURCE,OUT/'source.png');shutil.copy2(MASK,OUT/'edit-mask.png')
 h.require_idle(BASE);save(OUT,'run.json',h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}})))
 print('Submitted Qwen smooth metal edit')
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running',pid);return
 job=hist[pid];save(OUT,'history.json',job);assert job['status']['status_str']=='success',job['status']
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected Qwen smooth metal donor')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);globals()[p.parse_args().action]()
