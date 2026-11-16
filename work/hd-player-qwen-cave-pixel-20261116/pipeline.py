"""Four cave-matched pixel/grime sketches based on the accepted v4 study."""
from pathlib import Path
import argparse,importlib.util,sys,math as pymath
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116'
PREV=ROOT/'assets/generated/player-male-vault13/qwen-nose-fabric-v4-20261116'
SOURCE=PREV/'composite-v2/candidate-x6.png'
SOURCE4=PREV/'composite-v2/candidate-x4.png'
CAVE=ROOT/'build/hd-wall-grey-match-20261116/entrance-live-review.png'
spec=importlib.util.spec_from_file_location('v4',ROOT/'work/hd-player-qwen-nose-fabric-20261116/pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
h=p.h;h.OUT=OUT;Graph=p.Graph;math=p.math;rect=p.rect

def cached(d):
    if (d/'result.json').exists():return True
    if (d/'run.json').exists():h.execute(d,{},{});return True
    return False

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'plan.json').exists():
        h.save(OUT/'plan.json',dict(status='four sketches only, not installed',source=str(SOURCE.relative_to(ROOT)),source_sha256=h.sha(SOURCE),
            cave_reference=str(CAVE.relative_to(ROOT)),cave_reference_sha256=h.sha(CAVE),
            guide_sha256=h.sha(ROOT/'old-new-persons-model-converter.md'),
            pose_order=['stand-d2-f000','stand-d0-f000','walk-d2-f002','walk-d4-f006'],
            protected_heads_x6=[[155,116,67,74],[543,117,67,73],[151,676,68,83],[561,692,72,84]],
            method='Qwen cave-reference dirt/material pass, local body composite, restrained 2-HD-pixel RGB clusters; original x4 alpha preserved',
            pixel_grid_x4=2,pixel_blend=.5,
            qwen=dict(seed=161120269,steps=25,cfg=1,denoise=1,control_strength=.4,control_end=.65)))
        protected=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
        h.save(OUT/'runtime-art-baseline.json',{str(f.relative_to(ROOT)):h.sha(f) for f in protected if f.is_file()})
    d=OUT/'prepare-v2'
    if cached(d):return
    g=Graph();src=g.add('LoadImage',image=h.upload(SOURCE));alpha=g.add('InvertMask',mask=[src[0],1])
    g.save(g.add('Canny',image=g.add('MaskToImage',mask=alpha),low_threshold=.1,high_threshold=.3),'contours')
    cave=g.add('LoadImage',image=h.upload(CAVE))
    # Texture-only crop away from HUD and player: floor, wall strata, rocks, worn metal.
    cave=g.add('ImageCrop',image=cave,x=1056,y=128,width=768,height=576)
    g.save(g.scale(cave,640,480),'cave-style-reference')
    body=g.add('ThresholdMask',mask=alpha,value=.95)
    seed=g.add('LoadImage',image=h.upload(ROOT/'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116/control-v2/seed-reference.png'))
    dark=g.add('InvertMask',mask=[seed[0],1])
    dark=g.add('ThresholdMask',mask=dark,value=.5)
    for ch in ['red','green','blue']:
        channel=g.add('ImageToMask',image=seed,channel=ch)
        light=g.add('ThresholdMask',mask=channel,value=.12)
        dark=math(g,dark,g.add('InvertMask',mask=light),'multiply')
    dark=g.add('GrowMask',mask=dark,expand=4,tapered_corners=True)
    body=math(g,body,dark,'subtract')
    for x,y,w,he in h.read(OUT/'plan.json')['protected_heads_x6']:
        body=math(g,body,rect(g,768,1152,x,y,w,he),'subtract')
    g.save(g.add('MaskToImage',mask=body),'body-edit-mask')
    h.execute(d,g.g,g.outputs)

def qwen():
    d=OUT/'qwen'
    if cached(d):return
    prompt=('Image 1 is the edit target: FOUR male Vault 13 character sprites in a fixed transparent 2x2 atlas. '
        'Image 2 is ONLY a texture and atmosphere reference from their actual Fallout cave: dusty gray rock, muted brown dirt, '
        'worn metal, gritty restrained pixel-sized surface detail. Do not copy the cave scene, rock shapes or objects into the atlas. '
        'Make these SAME four sprites slightly more pixel-textured, dirty and grounded so they fit that environment. '
        'Keep the current dark indigo blue suit and yellow 13 trim, adult face, short brown hair, corrected projecting nose profile, '
        'body proportions, exact four poses and positions, scale, angles, original shadows and transparent background. '
        'Preserve the existing costume design; no new armor, panels, belts, props, tears or holes. '
        'Add visible but moderate gray-brown cave dust and worn cloth: smudged cuffs, dusty forearms, dirt in elbow and knee creases, '
        'light scuffs on the hips, dusty trouser hems and rubbed muddy-brown boot toes. The same wear logic across all views. '
        'Yellow trim and number 13 remain legible but become aged ochre cloth rather than fresh bright paint. '
        'Use small irregular pixel clusters and restrained broken shading, a little granular dither in transitions, '
        'like restored late-1990s pre-rendered Fallout sprites at HD scale. Slightly rougher and less sterile, still detailed and readable. '
        'Keep the face recognizable and naturally shaded. Keep large cloth folds and original upper-left light. '
        'Reduce clean glossy highlights, mute the blue saturation slightly, keep deep readable fabric color. '
        'Do not use giant pixels, chunky 8-bit caricature, black outlines, cel shading, random white speckles or a blanket noise filter. '
        'Do not turn the cloth into stone, gray camouflage or rusty armor. No gore or extreme grime. '
        'Output exactly the same four full figures in the same 2x2 layout, transparent RGBA between and around them. '
        'Do not add a scene, ground plane, captions or new characters.')
    g=Graph();src=g.add('LoadImage',image=h.upload(SOURCE));rgba=g.add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
    cave=g.add('LoadImage',image=h.upload(OUT/'prepare-v2/cave-style-reference.png'))
    edge=g.add('LoadImage',image=h.upload(OUT/'prepare-v2/contours.png'))
    model=g.add('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default')
    clip=g.add('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default')
    vae=g.add('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors')
    model=g.add('QwenImage21Cache',model=model,device='cpu',dtype='default')
    cond=g.add('TextEncodeQwenImage21',clip=clip,prompt=prompt,negative_prompt='',vae=vae,resolution=0,
        **{'images.image_1':rgba,'images.image_2':cave})
    patch=g.add('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors')
    model=g.add('ZImageFunControlnet',model=model,model_patch=patch,vae=vae,strength=.4,image=edge,start_percent=0.,end_percent=.65)
    latent=g.add('KSampler',model=model,positive=cond,negative=[cond[0],1],latent_image=[cond[0],2],seed=161120269,
        steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.)
    result=g.add('VAEDecode',samples=latent,vae=vae);g.save(result,'raw')
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    h.execute(d,g.g,g.outputs)

def finish():
    d=OUT/'finish-v2'
    if cached(d):return
    g=Graph();old=g.add('LoadImage',image=h.upload(SOURCE));old4=g.add('LoadImage',image=h.upload(SOURCE4))
    gen=g.add('LoadImage',image=h.upload(OUT/'qwen/raw.png'))
    maskim=g.add('LoadImage',image=h.upload(OUT/'prepare-v2/body-edit-mask.png'))
    # Soften the edit boundary inward; do not expand it onto the protected floor.
    mask=g.add('ImageToMask',image=maskim,channel='red')
    soft=g.add('ImageBlur',image=maskim,blur_radius=2,sigma=1.)
    mask=math(g,mask,g.add('ImageToMask',image=soft,channel='red'),'multiply')
    rgb=g.add('ImageCompositeMasked',destination=old,source=gen,x=0,y=0,resize_source=False,mask=mask)
    alpha=g.add('InvertMask',mask=[old[0],1])
    rgba=g.add('JoinImageWithAlpha',image=rgb,alpha=p.corrected_inverse(g,alpha))
    g.save(rgba,'material-master-x6')
    normal=g.scale(rgb,512,768)
    low=g.add('ImageScale',image=normal,upscale_method='area',width=256,height=384,crop='disabled')
    block=g.add('ImageScale',image=low,upscale_method='nearest-exact',width=512,height=768,crop='disabled')
    pixel=g.add('ImageBlend',image1=normal,image2=block,blend_factor=.5,blend_mode='normal')
    # Pixel texture is local to the figures; keep all existing floor RGB unchanged.
    mask4=g.scale(maskim,512,768)
    visible=g.add('ImageToMask',image=mask4,channel='red')
    visible=math(g,visible,g.add('ThresholdMask',mask=visible,value=.004),'multiply')
    for x,y,w,he in h.read(OUT/'plan.json')['protected_heads_x6']:
        left=pymath.floor(x/1.5);top=pymath.floor(y/1.5)
        width=pymath.ceil((x+w)/1.5)-left;height=pymath.ceil((y+he)/1.5)-top
        visible=math(g,visible,rect(g,512,768,left,top,width,height),'subtract')
    # Preserve the newly approved faces, including the nose, in this material study.
    finalrgb=g.add('ImageCompositeMasked',destination=old4,source=pixel,x=0,y=0,resize_source=False,mask=visible)
    inv=[old4[0],1];eps=g.add('SolidMask',value=.0000001,width=512,height=768)
    inv=math(g,inv,eps,'subtract')
    result=g.add('JoinImageWithAlpha',image=finalrgb,alpha=inv)
    g.save(result,'candidate-x4');g.save(g.add('MaskToImage',mask=visible),'edit-mask-x4')
    h.execute(d,g.g,g.outputs)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','qwen','finish']);args=ap.parse_args()
    {'prepare':prepare,'qwen':qwen,'finish':finish}[args.stage]()
