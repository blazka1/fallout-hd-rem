"""Colour-only local compositing on an untouched first-FLUX canvas."""
from pipeline import ROOT,BASE,OUT,BOXES,read,save,sha
from PIL import Image,ImageDraw,ImageFilter,ImageFont
import numpy as np
from scipy import ndimage as ndi

NECK=[[(117,101),(122,103),(129,110),(138,112),(142,110),(148,118),(146,130),(137,126),(128,119),(122,123),(117,115)],
      [(375,106),(395,107),(400,116),(376,118)],
      [(117,485),(122,487),(129,494),(138,496),(142,494),(148,502),(146,514),(137,510),(128,503),(122,507),(117,499)],
      [(364,515),(374,515),(383,509),(389,514),(382,527),(374,533),(366,545),(359,538),(360,526)]]
GLYPHS=[[(146,127),(156,127),(157,143),(146,144)],None,[(145,507),(159,507),(160,524),(145,525)],[(368,533),(381,533),(382,548),(368,548)]]
NUMBER=[(354,126),(403,128),(406,171),(354,173)]
HEADS=[[(116,72),(143,72),(147,81),(147,107),(140,113),(128,110),(119,102),(116,91)],
       [(373,76),(402,76),(402,101),(395,106),(377,105),(373,99)],
       [(116,456),(143,456),(147,465),(147,491),(140,497),(128,494),(119,486),(116,475)],
       [(361,480),(385,480),(391,491),(389,505),(379,509),(374,515),(365,517),(357,510),(356,498)]]

def polygon(poly,size=(512,768)):
    m=Image.new('L',size);ImageDraw.Draw(m).polygon(poly,fill=255);return m

def main():
    srcim=Image.open(OUT/'inputs/first-flux.png').convert('RGB');src=np.asarray(srcim)
    gen=Image.open(OUT/'local-edit/raw.png').convert('RGB');candidate=srcim.copy()
    for i,b in enumerate(BOXES):
        patch=gen.crop(((i%2)*256,(i//2)*256,(i%2+1)*256,(i//2+1)*256)).resize((128,128),Image.Resampling.LANCZOS)
        candidate.paste(patch,b[:2])
    candidate=np.asarray(candidate).copy()
    # This isolated badge patch was also generated directly from the first FLUX.
    chest=np.asarray(Image.open(OUT/'side-chest-only/raw.png').resize((64,64),Image.Resampling.LANCZOS))
    chest_layer=src.copy();chest_layer[512:576,344:408]=chest
    bg=np.median(np.concatenate([src[:16].reshape(-1,3),src[-16:].reshape(-1,3)]),axis=0)
    foreground=np.max(np.abs(src.astype(float)-bg),axis=2)>30
    interior=ndi.binary_erosion(foreground,iterations=2)
    head=np.zeros(src.shape[:2],dtype=bool)
    for poly in HEADS:head|=np.asarray(polygon(poly))>0
    out=src.astype(float);union=np.zeros(src.shape[:2],dtype=bool);mask_records=[];collar_repairs=[]
    maskdir=OUT/'masks';maskdir.mkdir(exist_ok=True)
    entries=[(f'neck-{i}',p,'main') for i,p in enumerate(NECK)]
    entries += [(f'chest-{i}',p,'side' if i==3 else 'main') for i,p in enumerate(GLYPHS) if p]
    entries += [('back-13',NUMBER,'main')]
    for name,poly,kind in entries:
        hard=np.asarray(polygon(poly))>0
        # Feather is entirely contained in an explicit, saved edit footprint.
        feather=np.asarray(polygon(poly).filter(ImageFilter.GaussianBlur(.75))).astype(float)/255
        footprint=ndi.binary_dilation(hard,iterations=2)&interior&~head
        feather*=footprint;feather[feather<.015]=0
        patch=(chest_layer if kind=='side' else candidate).astype(float).copy()
        if name.startswith('neck'):
            # Tone down only the newly generated bright blue neckline stitch.
            blue=(patch[:,:,2]-patch[:,:,0]>32)&(patch[:,:,2]-patch[:,:,1]>22)
            lum=patch@np.array([.2126,.7152,.0722])
            navy=lum[:,:,None]*np.array([.84,.98,1.10])
            patch=np.where(blue[:,:,None],navy,patch)
            # A few model pixels at the removed collar contain grey background.
            # Repair colour locally with a fixed translated cloth patch from the
            # original; no rescaling, nearest-edge projection, or body deformation.
            bad=(np.max(np.abs(patch-bg),axis=2)<42)&(feather>0)
            yi,xi=np.where(bad)
            offsets=[(-8,24),(14,18),(-8,24),(15,14)]
            dx,dy=offsets[int(name[-1])]
            patch[yi,xi]=src[yi+dy,xi+dx]
            collar_repairs.append(dict(region=name,pixels=len(xi),cloth_translation=[dx,dy]))
        out=out*(1-feather[:,:,None])+patch*feather[:,:,None]
        active=feather>0;union|=active
        Image.fromarray(np.rint(feather*255).astype('uint8')).save(maskdir/(name+'.png'))
        mask_records.append(dict(name=name,polygon=poly,source=kind,pixels=int(active.sum())))
    # Remove tiny ochre collar tips that lie on the original edge. Colour changes
    # stay on the same foreground pixels; their coordinates/coverage never move.
    collar_tips=[[(116,100),(122,103),(125,118),(120,121),(116,114)],
                 [(374,106),(396,107),(400,116),(375,117)],
                 [(116,484),(122,487),(125,502),(120,505),(116,498)],
                 [(381,509),(391,511),(389,519),(379,526)]]
    tips=np.zeros(src.shape[:2],dtype=bool)
    for i,poly in enumerate(collar_tips):
        region=np.asarray(polygon(poly))>0
        rr,gg,bb=out[:,:,0],out[:,:,1],out[:,:,2]
        yellow=(gg>rr*.82)&(rr>80)&(bb<gg*.78)&(rr>bb*1.3)
        m=region&yellow&foreground&~head
        yi,xi=np.where(m);dx,dy=[(-8,24),(14,18),(-8,24),(15,14)][i]
        out[yi,xi]=src[yi+dy,xi+dx];tips|=m
    union|=tips
    Image.fromarray((tips*255).astype('uint8')).save(maskdir/'collar-tip-colour-only.png')
    edited=np.clip(np.rint(out),0,255).astype('uint8')
    # Very weak monochrome grain, on cloth interiors only; no global re-render.
    a=src.astype(float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    cloth=(b-r>8)&(b-g>1)&(r<140)&(np.max(a,axis=2)-np.min(a,axis=2)>10)
    cloth=ndi.binary_erosion(cloth,iterations=1)&interior&~head
    spatial=np.zeros(cloth.shape,dtype=bool)
    for rect in [(70,112,172,299),(330,115,438,317),(70,500,184,695),(323,525,439,694)]:
        x1,y1,x2,y2=rect;spatial[y1:y2,x1:x2]=True
    cloth&=spatial
    grain=ndi.gaussian_filter(cloth.astype(float),.65)*cloth
    noise=np.random.default_rng(1711202713).normal(0,1.15,cloth.shape)*grain
    final=np.clip(np.rint(edited.astype(float)+noise[:,:,None]),0,255).astype('uint8')
    dest=OUT/'final';dest.mkdir(exist_ok=True)
    Image.fromarray(edited).save(dest/'local-edits-before-grain.png');Image.fromarray(final).save(dest/'four-poses.png')
    Image.fromarray((union*255).astype('uint8')).save(maskdir/'all-local-edits.png')
    Image.fromarray((grain*255).astype('uint8')).save(maskdir/'grain-cloth-only.png')
    Image.fromarray((head*255).astype('uint8')).save(maskdir/'protected-heads.png')
    Image.fromarray(((foreground&~interior)*255).astype('uint8')).save(maskdir/'protected-edges.png')
    # Exact pixel invariants, not silhouette-IoU claims after a forced alpha mask.
    diff=np.any(final!=src,axis=2);localdiff=np.any(edited!=src,axis=2)
    allowed=union|(grain>0);edge=foreground&~interior
    final_fg=np.max(np.abs(final.astype(float)-bg),axis=2)>30
    checks=dict(size_unchanged=final.shape==src.shape,
        outside_local_masks_before_grain_exact=bool(np.array_equal(edited[~union],src[~union])),
        outside_authorized_masks_final_exact=bool(np.array_equal(final[~allowed],src[~allowed])),
        protected_heads_exact=bool(np.array_equal(final[head],src[head])),
        silhouette_edges_except_authorized_collar_colour_exact=bool(np.array_equal(final[edge&~tips],src[edge&~tips])),
        background_and_shadow_outside_cloth_exact=bool(np.array_equal(final[~allowed],src[~allowed])),
        threshold_foreground_shape_exact=bool(np.array_equal(foreground,final_fg)),
        source_first_flux_hash_exact=sha(BASE/'edit-v1/raw.png')==read(OUT/'plan.json')['source_sha256'])
    # Shadows are below each torso and outside blue cloth; compare explicit strips.
    shadow_regions=np.zeros(src.shape[:2],dtype=bool)
    for i in range(4):
        cx=(i%2)*256;cy=(i//2)*384
        shadow_regions[cy+265:cy+350,cx+25:cx+235]=True
    shadow_regions&=~cloth
    checks['floor_shadow_regions_exact']=bool(np.array_equal(final[shadow_regions],src[shadow_regions]))
    Image.fromarray((shadow_regions*255).astype('uint8')).save(maskdir/'protected-floor-regions.png')
    Image.fromarray(np.clip(np.abs(final.astype(float)-src)*5,0,255).astype('uint8')).save(maskdir/'difference-amplified-x5.png')
    before=read(OUT/'runtime-before.json');changed=[p for p,h in before.items() if sha(ROOT/p)!=h]
    checks['runtime_unchanged']=not changed
    checks['pixel_art_still_paused']=read(ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116/paused.json')['do_not_auto_resume']
    save(OUT/'qa.json',dict(status='four-frame local edit; no pose/contour transforms',checks=checks,
        all_pass=all(checks.values()),edited_pixels_before_grain=int(localdiff.sum()),changed_pixels_total=int(diff.sum()),
        runtime_files_checked=len(before),runtime_changed=changed,
        model_jobs=[read(OUT/n/'result.json') for n in ['local-edit','side-chest-only']],
        final_sha256=sha(dest/'four-poses.png'),geometry_transforms=[],collar_tip_colour_pixels=int(tips.sum()),
        note='Foreground threshold is a diagnostic; exact outside-mask pixel comparison is the hard constraint.'))
    save(OUT/'compositing.json',dict(crop_boxes=BOXES,uniform_crop_scale=2,output_canvas_scale=1,
        edit_masks=mask_records,collar_colour_repairs=collar_repairs,grain=dict(seed=1711202713,sigma_rgb=1.15,monochrome=True,region='blue cloth interior only'),
        pose_warp=False,source_alpha_substitution=False,nonuniform_scaling=False,global_colour_correction=False))
    previews(srcim,Image.fromarray(final))
    print(dict(checks=checks,edited_pixels=int(localdiff.sum()),total_changed=int(diff.sum())),flush=True)
    assert all(checks.values())

def previews(before,after):
    out=OUT/'preview';out.mkdir(exist_ok=True)
    poses=read(BASE/'plan.json')['poses']
    def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
    def board(rows,path):
        im=Image.new('RGB',(1000,98+298*len(rows)+28),(25,28,29));d=ImageDraw.Draw(im)
        d.text((16,13),'Первый FLUX · только локальные правки',font=font(25),fill=(229,220,191))
        d.text((16,51),'Без изменения поз и силуэтов · исходные тени · слабое зерно на ткани',font=font(17),fill=(176,187,178))
        for j,(title,atlas) in enumerate(rows):
            y=98+j*298;d.text((16,y+24),title,font=font(21),fill=(232,216,166))
            for i,p in enumerate(poses):
                box=(p['x']*4-8,p['y']*4-8,(p['x']+p['width'])*4+8,(p['y']+p['height'])*4+8)
                sp=atlas.crop(box);tile=Image.new('RGB',(198,288),(163,165,167));tile.paste(sp,((198-sp.width)//2,278-sp.height))
                im.paste(tile,(184+204*i,y))
        im.save(path)
    board([('После правок',after)],out/'four-poses.png');board([('Первый FLUX',before),('Локальные\nправки',after)],out/'before-after.png')
    # Same crops, same uniform inspection enlargement: never part of final artwork.
    im=Image.new('RGB',(1024,560),(25,28,29));d=ImageDraw.Draw(im)
    for row,atlas in enumerate([before,after]):
        for i,b in enumerate(BOXES):im.paste(atlas.crop(b).resize((256,256),Image.Resampling.NEAREST),(i*256,row*280+24))
        d.text((8,row*280+2),'До' if row==0 else 'После · увеличенные фрагменты',font=font(16),fill=(230,217,180))
    im.save(out/'details-before-after.png')

if __name__=='__main__':main()
