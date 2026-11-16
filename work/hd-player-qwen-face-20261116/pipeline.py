"""One Qwen face study; crop preparation and local compositing run in ComfyUI."""
from pathlib import Path
import argparse, importlib.util, sys, uuid
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/generated/player-male-vault13/qwen-face-v3-20261116'
PREV = ROOT / 'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116'
SOURCE = PREV / 'qwen-soft/raw-x6.png'
spec = importlib.util.spec_from_file_location('helpers', ROOT / 'work/cave-variety-seed-qwen-20261115/pipeline.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h); h.OUT = OUT
# Crop origins in the existing x6 atlas; face rectangles are crop-local x,y,w,h.
FACES = [dict(pose='stand-d2-f000', x=128, y=96, face=[41, 44, 44, 47]),
         dict(pose='walk-d2-f002', x=124, y=656, face=[40, 48, 46, 50]),
         dict(pose='walk-d4-f006', x=532, y=676, face=[39, 46, 45, 48])]

class Graph:
    def __init__(self): self.g = {}; self.outputs = {}; self.prefix = 'fallout1_player_face/' + uuid.uuid4().hex
    def add(self, kind, **inputs):
        k = str(len(self.g) + 1); self.g[k] = h.node(kind, **inputs); return [k, 0]
    def save(self, image, name):
        k = self.add('SaveImage', images=image, filename_prefix=self.prefix + '/' + name)[0]
        self.outputs[k] = name + '.png'
    def stitch(self, images):
        image = images[0]
        for other in images[1:]:
            image = self.add('ImageStitch', image1=image, image2=other, direction='right', match_image_size=False, spacing_width=0, spacing_color='black')
        return image
    def scale(self, image, w, height):
        return self.add('ImageScale', image=image, upscale_method='lanczos', width=w, height=height, crop='disabled')

def cached(d):
    if (d / 'result.json').exists(): return True
    if (d / 'run.json').exists(): h.execute(d, {}, {}); return True
    return False

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / 'plan.json').exists():
        h.save(OUT / 'plan.json', dict(status='preview only', source=str(SOURCE.relative_to(ROOT)), source_sha256=h.sha(SOURCE),
            guide_sha256=h.sha(ROOT / 'old-new-persons-model-converter.md'), faces=FACES,
            scope='Three visible faces only; rear view and original global alpha are preserved',
            crop_size=[128,128], qwen_atlas=[1152,384], result_atlas=[768,1152], export=[512,768],
            method='Qwen edit of enlarged head crops, then feathered local RGB composite in ComfyUI. Not a free silhouette regeneration.',
            qwen=dict(seed=161120266, steps=25, cfg=1, denoise=1, control_strength=.25, control_end=.55)))
        protected=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
        h.save(OUT/'runtime-art-baseline.json',{str(p.relative_to(ROOT)):h.sha(p) for p in protected if p.is_file()})
    d=OUT/'prepare'
    if cached(d): return
    g=Graph(); src=g.add('LoadImage',image=h.upload(SOURCE))
    rgba=g.add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
    alpha=g.add('InvertMask',mask=[src[0],1]); crops=[]; masks=[]
    for f in FACES:
        crops.append(g.add('ImageCrop',image=rgba,x=f['x'],y=f['y'],width=128,height=128))
        m=g.add('CropMask',mask=alpha,x=f['x'],y=f['y'],width=128,height=128)
        masks.append(g.add('MaskToImage',mask=m))
    heads=g.scale(g.stitch(crops),1152,384)
    edges=g.add('Canny',image=g.scale(g.stitch(masks),1152,384),low_threshold=.1,high_threshold=.3)
    g.save(heads,'head-reference'); g.save(edges,'head-contours')
    h.execute(d,g.g,g.outputs)

def qwen():
    d=OUT/'qwen'
    if cached(d): return
    prompt=('Edit these THREE enlarged head-and-shoulder crops of the SAME male Fallout Vault 13 character. '
        'Change the face to look like a believable ordinary adult man around thirty, with calm alert eyes and a relaxed closed mouth. '
        'Use a more natural, slightly oval face: moderate cheekbones, a less blocky jaw, a normal-sized nose and chin, '
        'relaxed eyebrows instead of a heavy scowling brow, natural eyelids and small realistically shaded eyes. '
        'Give the skin subtle warm and cool variations, soft transitions on cheeks and forehead, gentle nasolabial definition and natural lips. '
        'The face should feel alive and human rather than a generic stern action figure. Do not exaggerate facial planes or add a forced smile. '
        'Keep him clean-shaven with the existing short brown hair. No beard, scars, glasses, makeup or new accessories. '
        'Maintain the SAME face identity across all three views. Preserve each exact head size, head position, viewing direction, '
        'downward isometric camera angle, ear position, neck connection and lighting from upper left. '
        'Left and middle show the original three-quarter face, right shows the original left-facing profile. Do not turn any head toward the viewer. '
        'Keep the original hair silhouette and all blue/yellow clothing unchanged. Three fixed crops in one horizontal row, no repositioning. '
        'Detailed realistic pre-rendered RPG game art, with readable face features at sprite scale. '
        'Avoid waxy plastic skin, cartoon eyes, superhero jaw, harsh brow shadow, facial outlines and glossy skin. '
        'Transparent background with alpha zero, no labels, borders, scene or extra faces.')
    g=Graph(); src=g.add('LoadImage',image=h.upload(OUT/'prepare/head-reference.png'))
    rgba=g.add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
    edge=g.add('LoadImage',image=h.upload(OUT/'prepare/head-contours.png'))
    model=g.add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
    clip=g.add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
    vae=g.add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
    model=g.add('QwenImage21Cache',model=model,device='cpu',dtype='default')
    cond=g.add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':rgba})
    patch=g.add('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors')
    model=g.add('ZImageFunControlnet',model=model,model_patch=patch,vae=vae,strength=.25,image=edge,start_percent=0.,end_percent=.55)
    samples=g.add('KSampler',model=model,positive=cond,negative=[cond[0],1],latent_image=[cond[0],2],seed=161120266,
        steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
    decoded=g.add('VAEDecode',samples=samples,vae=vae); g.save(decoded,'heads-raw')
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    h.execute(d,g.g,g.outputs)

def composite(lossless=True):
    d=OUT/('composite-lossless' if lossless else 'composite')
    if cached(d): return
    g=Graph(); original=g.add('LoadImage',image=h.upload(SOURCE))
    alpha=g.add('InvertMask',mask=[original[0],1]); new=g.add('LoadImage',image=h.upload(OUT/'qwen/heads-raw.png'))
    rgb=original; total=g.add('SolidMask',value=0.,width=768,height=1152)
    for i,f in enumerate(FACES):
        crop=g.add('ImageCrop',image=new,x=i*384,y=0,width=384,height=384); crop=g.scale(crop,128,128)
        x,y,w,he=f['face']
        rect=g.add('SolidMask',value=1.,width=w,height=he)
        rect=g.add('FeatherMask',mask=rect,left=3,top=3,right=3,bottom=4)
        empty=g.add('SolidMask',value=0.,width=128,height=128)
        mask=g.add('MaskComposite',destination=empty,source=rect,x=x,y=y,operation='add')
        a=g.add('CropMask',mask=alpha,x=f['x'],y=f['y'],width=128,height=128)
        mask=g.add('MaskComposite',destination=mask,source=a,x=0,y=0,operation='multiply')
        rgb=g.add('ImageCompositeMasked',destination=rgb,source=crop,x=f['x'],y=f['y'],resize_source=False,mask=mask)
        total=g.add('MaskComposite',destination=total,source=mask,x=f['x'],y=f['y'],operation='add')
    inverse_alpha=[original[0],1]
    if lossless:
        # LoadImage stores 1-alpha; JoinImageWithAlpha inverts it again. A tiny
        # float bias avoids truncating some original 8-bit alpha values by one.
        bias=g.add('SolidMask',value=0.0000001,width=768,height=1152)
        inverse_alpha=g.add('MaskComposite',destination=inverse_alpha,source=bias,x=0,y=0,operation='subtract')
    rgba=g.add('JoinImageWithAlpha',image=rgb,alpha=inverse_alpha)
    g.save(rgba,'candidate-x6'); g.save(g.scale(rgba,512,768),'candidate-x4')
    g.save(g.add('MaskToImage',mask=total),'edit-mask-x6')
    h.execute(d,g.g,g.outputs)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','qwen','composite']);a=p.parse_args()
    {'prepare':prepare,'qwen':qwen,'composite':composite}[a.stage]()
