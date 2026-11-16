"""Qwen profile and fabric study with a localized bounded alpha change."""
from pathlib import Path
import argparse, importlib.util, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/qwen-nose-fabric-v4-20261116'
PREV=ROOT/'assets/generated/player-male-vault13/qwen-face-v3-20261116'
SOURCE=PREV/'composite-lossless/candidate-x6.png'
spec=importlib.util.spec_from_file_location('face',ROOT/'work/hd-player-qwen-face-20261116/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
h=p.h;h.OUT=OUT;Graph=p.Graph

def cached(d):
    if (d/'result.json').exists():return True
    if (d/'run.json').exists():h.execute(d,{},{});return True
    return False

def math(g,a,b,op):return g.add('MaskComposite',destination=a,source=b,x=0,y=0,operation=op)
def threshold(g,m,v):return g.add('ThresholdMask',mask=m,value=v)
def rect(g,w,hgt,x,y,rw,rh,feather=0):
    canvas=g.add('SolidMask',value=0.,width=w,height=hgt)
    patch=g.add('SolidMask',value=1.,width=rw,height=rh)
    if feather:patch=g.add('FeatherMask',mask=patch,left=feather,top=feather,right=feather,bottom=feather)
    return g.add('MaskComposite',destination=canvas,source=patch,x=x,y=y,operation='add')
def corrected_inverse(g,alpha):
    inv=g.add('InvertMask',mask=alpha)
    eps=g.add('SolidMask',value=.0000001,width=768,height=1152)
    return math(g,inv,eps,'subtract')

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'plan.json').exists():
        h.save(OUT/'plan.json',dict(status='preview only',source=str(SOURCE.relative_to(ROOT)),source_sha256=h.sha(SOURCE),
            guide_sha256=h.sha(ROOT/'old-new-persons-model-converter.md'),
            profile_crop=[532,676,128,128],profile_working=[512,512],body_working=[768,1152],
            alpha_corridor_x6=4,alpha_corridor_x4=4/1.5,
            alpha_edit_region_x6=[562,720,30,42],face_rgb_edit_region_x6=[562,716,58,60],
            notes=['Preserve CE registration and all four poses',
                'Original alpha is released only around fourth-pose profile, inside a four-pixel x6 corridor',
                'Original blue/yellow garment color selection limits fabric changes; heads, floor, hands and boots are protected',
                'All artistic operations run in ComfyUI; no procedural paint or noise in Python']))
        protected=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
        h.save(OUT/'runtime-art-baseline.json',{str(f.relative_to(ROOT)):h.sha(f) for f in protected if f.is_file()})
    d=OUT/'prepare-v2'
    if cached(d):return
    g=Graph();src=g.add('LoadImage',image=h.upload(SOURCE));alpha=g.add('InvertMask',mask=[src[0],1])
    rgba=g.add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
    crop=g.add('ImageCrop',image=rgba,x=532,y=676,width=128,height=128)
    g.save(g.scale(crop,512,512),'profile-reference')
    edges=g.add('Canny',image=g.add('MaskToImage',mask=alpha),low_threshold=.1,high_threshold=.3)
    g.save(edges,'body-contours')
    r=g.add('ImageToMask',image=src,channel='red'); green=g.add('ImageToMask',image=src,channel='green');b=g.add('ImageToMask',image=src,channel='blue')
    blue=math(g,threshold(g,math(g,b,r,'subtract'),.06),threshold(g,math(g,b,green,'subtract'),.015),'multiply')
    blue=math(g,blue,threshold(g,b,.32),'multiply')
    # Blue-only selection protects skin, hair, boots and the yellow insignia.
    cloth=math(g,blue,threshold(g,alpha,.95),'multiply')
    # Exclude floor-shadow zones and bare hands explicitly in addition to color selection.
    for x,y,w,he in [(0,478,384,98),(384,470,384,106),(0,1040,384,112),(384,1040,384,112)]:
        cloth=math(g,cloth,rect(g,768,1152,x,y,w,he),'subtract')
    g.save(g.add('MaskToImage',mask=cloth),'cloth-mask')
    h.execute(d,g.g,g.outputs)

def qwen(profile=False):
    d=OUT/('qwen-profile' if profile else 'qwen-fabric')
    if cached(d):return
    if profile:
        prompt=('Edit this single left-facing three-quarter/profile head of the same adult male Vault 13 character. '
            'Correct ONLY his flattened nose profile. Give him a normal anatomically clear nasal bridge, a distinct rounded projecting tip, '
            'a small nostril and a short underside above the upper lip. The tip should project a little farther LEFT, roughly 8 to 12 pixels '
            'at this 512-pixel image size, so the nose does not blend into a flat forehead-to-mouth slope. '
            'A normal proportioned human nose, not a long pointed caricature, not a bulbous nose. '
            'The slight extension of the nose silhouette is intentional and allowed. Keep the forehead, head center, eyes, mouth, jaw, ears, '
            'short brown hair, neck, blue/yellow collar and shoulders in their exact original positions. '
            'Keep the same man, age, clean-shaven face and serious natural expression. Keep exactly the same downward isometric camera '
            'and left-facing direction; do not rotate the head to show more of the front. '
            'Match existing realistic pre-rendered RPG shading and skin tone, light from upper left. '
            'Keep transparent background, no scene, text, border or other people.')
        source=OUT/'prepare-v2/profile-reference.png'
    else:
        prompt=('Edit this transparent RGBA 2x2 atlas of FOUR identical male Fallout Vault 13 game sprites. '
            'Change ONLY the MATERIAL of the existing blue and yellow jumpsuit. '
            'Make the blue fabric moderately darker, around 15 to 20 percent, a muted deep indigo workwear blue, still clearly readable in shadow. '
            'Replace the sterile smooth surface with believable matte tightly woven cotton twill: visible subtle diagonal weave, '
            'small irregularities in the fabric, a little lint and restrained rubbing along existing seams, elbows and knees. '
            'Add faint accumulated grime in creases and slight wear on cuffs and hems. The suit is used but well kept: no tears, holes, '
            'large stains, patchwork, camouflage, random speckles, noisy grain, new panels, pockets, armor or accessories. '
            'Retain the same natural cloth folds and broad readable blue planes. Yellow collar, front stripe, waistband and number 13 '
            'remain the same shape and warm muted yellow, with subtle fabric texture and mild age. '
            'Preserve the exact four poses, head and face identity, hair, hands, boots, proportions, positions, scale, alpha silhouette, '
            'foot contacts, camera and original ground shadows. Do not change the face, body anatomy, costume design or lighting direction. '
            'Realistic pre-rendered isometric RPG art, rough matte fabric with reduced glossy highlights, no plastic or rubber. '
            'Keep the exact transparent atlas layout, no background or floor surface, no labels or additional figures.')
        source=SOURCE
    g=Graph();src=g.add('LoadImage',image=h.upload(source));rgba=g.add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
    model=g.add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
    clip=g.add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
    vae=g.add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
    model=g.add('QwenImage21Cache',model=model,device='cpu',dtype='default')
    cond=g.add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,**{'images.image_1':rgba})
    if not profile:
        edge=g.add('LoadImage',image=h.upload(OUT/'prepare-v2/body-contours.png'))
        patch=g.add('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors')
        model=g.add('ZImageFunControlnet',model=model,model_patch=patch,vae=vae,strength=.4,image=edge,start_percent=0.,end_percent=.65)
    latent=g.add('KSampler',model=model,positive=cond,negative=[cond[0],1],latent_image=[cond[0],2],seed=(161120268 if profile else 161120267),
        steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
    result=g.add('VAEDecode',samples=latent,vae=vae);g.save(result,'raw')
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    h.execute(d,g.g,g.outputs)

def maskfix():
    d=OUT/'mask-floor-protection'
    if cached(d):return
    g=Graph();seed=g.add('LoadImage',image=h.upload(ROOT/'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116/control-v2/seed-reference.png'))
    channel=g.add('ImageToMask',image=seed,channel='blue')
    dark=g.add('InvertMask',mask=threshold(g,channel,.12))
    dark=math(g,dark,threshold(g,g.add('InvertMask',mask=[seed[0],1]),.5),'multiply')
    dark=g.add('GrowMask',mask=dark,expand=4,tapered_corners=True)
    cm=g.add('LoadImage',image=h.upload(OUT/'prepare-v2/cloth-mask.png'))
    cloth=g.add('ImageToMask',image=cm,channel='red');cloth=math(g,cloth,dark,'subtract')
    g.save(g.add('MaskToImage',mask=cloth),'cloth-mask');g.save(g.add('MaskToImage',mask=dark),'protected-original-dark-shadows')
    h.execute(d,g.g,g.outputs)

def composite():
    d=OUT/'composite-v2'
    if cached(d):return
    g=Graph();old=g.add('LoadImage',image=h.upload(SOURCE));oa=g.add('InvertMask',mask=[old[0],1])
    fabric=g.add('LoadImage',image=h.upload(OUT/'qwen-fabric/raw.png'))
    # Qwen added weave but measured slightly brighter than the input. Apply the
    # requested modest darkening explicitly, only through the garment mask.
    black=g.add('EmptyImage',width=768,height=1152,batch_size=1,color=0)
    fabric=g.add('ImageBlend',image1=fabric,image2=black,blend_factor=.15,blend_mode='normal')
    maskim=g.add('LoadImage',image=h.upload(OUT/'mask-floor-protection/cloth-mask.png'))
    cloth=g.add('ImageToMask',image=maskim,channel='red')
    # Slightly soften color-selection boundaries without changing the costume silhouette.
    smooth=g.add('ImageBlur',image=maskim,blur_radius=1,sigma=.6)
    cloth=g.add('ImageToMask',image=smooth,channel='red');cloth=math(g,cloth,oa,'multiply')
    rgb=g.add('ImageCompositeMasked',destination=old,source=fabric,x=0,y=0,resize_source=False,mask=cloth)
    prof=g.add('LoadImage',image=h.upload(OUT/'qwen-profile/raw.png'))
    prgba=g.add('JoinImageWithAlpha',image=prof,alpha=[prof[0],1]);prgba=g.scale(prgba,128,128)
    split=g.add('SplitImageWithAlpha',image=prgba)
    pa=g.add('InvertMask',mask=[split[0],1])
    # SplitImageWithAlpha returns inverse alpha, matching JoinImageWithAlpha.
    base_binary=threshold(g,oa,.5)
    outer=g.add('GrowMask',mask=base_binary,expand=4,tapered_corners=True)
    inner=g.add('GrowMask',mask=base_binary,expand=-4,tapered_corners=True)
    empty=g.add('SolidMask',value=0.,width=768,height=1152)
    pa=g.add('MaskComposite',destination=empty,source=pa,x=532,y=676,operation='add')
    bounded=math(g,pa,outer,'multiply')
    bounded=math(g,math(g,bounded,g.add('InvertMask',mask=inner),'multiply'),inner,'add')
    alpha_roi=rect(g,768,1152,562,720,30,42,2)
    new_a=math(g,math(g,oa,g.add('InvertMask',mask=alpha_roi),'multiply'),math(g,bounded,alpha_roi,'multiply'),'add')
    face_mask=rect(g,128,128,30,40,58,60,3)
    face_cloth=g.add('CropMask',mask=cloth,x=532,y=676,width=128,height=128)
    face_mask=math(g,face_mask,face_cloth,'subtract')
    rgb=g.add('ImageCompositeMasked',destination=rgb,source=split,x=532,y=676,resize_source=False,mask=face_mask)
    rgba=g.add('JoinImageWithAlpha',image=rgb,alpha=corrected_inverse(g,new_a))
    g.save(rgba,'candidate-x6');g.save(g.scale(rgba,512,768),'candidate-x4')
    g.save(g.add('MaskToImage',mask=cloth),'cloth-mask-used')
    g.save(g.add('MaskToImage',mask=alpha_roi),'alpha-edit-region')
    g.save(g.add('MaskToImage',mask=new_a),'alpha-final')
    h.execute(d,g.g,g.outputs)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','fabric','profile','maskfix','composite']);args=ap.parse_args()
    {'prepare':prepare,'fabric':qwen,'profile':lambda:qwen(True),'maskfix':maskfix,'composite':composite}[args.stage]()
