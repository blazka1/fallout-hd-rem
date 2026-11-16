"""Explicit geometric retargeting and native-shadow preservation after FLUX edits.

Landmark coordinates are local x4 cell coordinates. No texture is painted by hand.
"""
from pipeline import ROOT,OUT,PREV,read,save,sha
from geometry import masks
from PIL import Image,ImageDraw,ImageFilter
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator,LinearNDInterpolator

# target original -> edited FLUX, inspected on geometry/*-grid.png.
POINTS=[
 [([128,82],[130,75]),([121,94],[122,90]),([137,95],[141,91]),([135,111],[137,106]),([126,119],[130,116]),
  ([105,126],[100,127]),([155,120],[157,120]),([83,147],[82,149]),([78,174],[79,174]),([80,202],[82,201]),([81,213],[84,214]),
  ([162,150],[164,148]),([164,175],[165,178]),([166,190],[166,196]),
  ([113,179],[113,179]),([139,180],[144,181]),([125,203],[130,211]),([109,222],[113,225]),([147,222],[155,225]),
  ([108,247],[111,251]),([157,249],[164,251]),([91,290],[91,292]),([167,287],[170,292]),
  ([89,310],[92,311]),([97,325],[100,330]),([170,304],[171,308]),([177,311],[180,313])],
 [([128,84],[131,80]),([128,107],[132,105]),([126,119],[130,116]),
  ([94,128],[103,126]),([149,135],[156,133]),([80,165],[83,164]),([80,201],[86,203]),([82,213],[89,215]),
  ([159,178],[167,178]),([163,212],[172,216]),([162,225],[174,227]),
  ([110,185],[112,184]),([142,185],[150,184]),([126,209],[134,213]),
  ([108,249],[109,249]),([154,250],[161,251]),([89,289],[94,304]),([163,302],[168,308]),
  ([89,305],[94,322]),([85,312],[92,331]),([166,320],[171,327]),([177,323],[180,327])],
 [([128,76],[130,76]),([127,92],[129,91]),([133,109],[137,104]),([130,119],[132,113]),
  ([104,122],[101,123]),([159,116],[157,117]),([81,150],[81,149]),([80,181],[81,182]),([82,192],[84,195]),
  ([171,150],[170,150]),([175,184],[177,182]),([174,202],[177,201]),
  ([117,175],[117,175]),([141,177],[146,175]),([133,210],[137,212]),
  ([117,237],[116,245]),([129,245],[141,244]),([109,258],[102,265]),([112,272],[111,281]),
  ([139,283],[145,283]),([145,303],[152,307]),([154,319],[160,321]),([161,325],[168,321])],
 [([121,104],[119,98]),([108,113],[106,111]),([116,128],[115,125]),([128,136],[128,132]),
  ([118,152],[123,148]),([150,150],[153,150]),([106,183],[105,186]),([95,205],[92,211]),
  ([162,185],[166,185]),([173,216],[175,215]),([175,230],[179,230]),
  ([115,199],[118,201]),([143,199],[147,200]),([129,222],[135,221]),
  ([92,264],[103,265]),([66,305],[76,315]),([52,316],[62,323]),([42,314],[50,321]),
  ([171,264],[162,263]),([195,298],[190,297]),([199,310],[186,314]),([211,305],[207,300])]
]

def corrected_material():
    raw=Image.open(OUT/'edit-two-references/raw.png').convert('RGB')
    neck=Image.open(OUT/'neckline-edit/raw.png').convert('RGB')
    boxes=read(OUT/'inputs/neckline-crop-boxes.json')
    polys=[[(173,150),(184,151),(204,162),(218,160),(226,181),(219,204),(198,192),(173,182)],
           [(554,155),(598,157),(607,179),(555,180)],
           [(173,726),(184,727),(204,738),(218,736),(226,757),(219,780),(198,768),(173,758)],
           [(545,760),(563,771),(580,758),(593,778),(578,798),(549,816),(532,797)]]
    combined=raw.copy();allmask=Image.new('L',raw.size)
    for i,(box,poly) in enumerate(zip(boxes,polys)):
        patch=neck.crop(((i%2)*256,(i//2)*256,(i%2+1)*256,(i//2+1)*256)).resize((128,128),Image.Resampling.LANCZOS)
        mask=Image.new('L',raw.size);ImageDraw.Draw(mask).polygon(poly,fill=255);mask=mask.filter(ImageFilter.GaussianBlur(3))
        layer=raw.copy();layer.paste(patch,box[:2]);combined.paste(layer,(0,0),mask)
        allmask=Image.fromarray(np.maximum(np.asarray(allmask),np.asarray(mask)))
    combined.save(OUT/'material-neckline-corrected-x6.png');allmask.save(OUT/'neckline-composite-mask-x6.png')
    save(OUT/'neckline-composite.json',dict(crop_boxes=boxes,polygons=polys,feather_working_pixels=3,
         method='Only FLUX neckline output composited locally; no hand-painted replacement pixels'))
    return combined.resize((512,768),Image.Resampling.LANCZOS)

SOURCE_LOWER=[
 [[(99,245),(121,250),(114,272),(101,303),(99,314),(114,327),(106,336),(93,337),(83,330),(79,316),(84,294),(86,273)],
  [(148,243),(170,243),(173,277),(176,296),(185,301),(190,311),(185,322),(168,319),(152,310),(149,295)]],
 [[(91,245),(119,249),(108,277),(105,312),(104,329),(98,339),(84,339),(79,326),(87,311),(85,278)],
  [(148,244),(173,245),(173,278),(178,311),(186,318),(188,330),(180,338),(159,339),(153,327),(156,308),(153,276)]],
 [[(101,245),(122,247),(116,262),(120,276),(117,286),(105,288),(93,276),(87,263)],
  [(128,242),(149,242),(151,275),(157,300),(174,315),(172,325),(155,330),(144,320),(137,292),(131,274)]],
 [[(89,275),(111,277),(91,308),(85,323),(82,337),(63,339),(48,331),(43,322),(49,316),(67,316),(75,299)],
  [(170,276),(187,275),(199,290),(215,298),(216,306),(207,310),(198,320),(183,326),(173,324),(172,316),(184,299)]]
]

def source_mask(rgb,i):
    a=np.asarray(rgb).astype(float)
    bg=np.median(np.concatenate([a[:16].reshape(-1,3),a[:,:16].reshape(-1,3)]),axis=0)
    m=np.max(np.abs(a-bg),axis=2)>24
    # Grey floor shadows cannot be separated from dark cloth by chroma alone.
    # Explicit inspected lower-leg/boot regions isolate them geometrically.
    allowed=Image.new('L',rgb.size);d=ImageDraw.Draw(allowed)
    cutoff=260 if i<3 else 286
    d.rectangle((0,0,255,cutoff),fill=255)
    for poly in SOURCE_LOWER[i]:d.polygon(poly,fill=255)
    m&=np.asarray(allowed)>0
    m=ndi.binary_closing(m,iterations=1)
    labels,n=ndi.label(m);sizes=np.bincount(labels.ravel());sizes[0]=0
    m=labels==sizes.argmax();m=ndi.binary_fill_holes(m)
    return m

def main():
    material=corrected_material();plan=read(OUT/'plan.json');poses=plan['poses']
    dest=OUT/'registered';dest.mkdir(exist_ok=True);dbg=OUT/'geometry'
    full=Image.new('RGBA',(512,768));rawfull=Image.new('RGBA',(512,768));metrics=[]
    save(OUT/'registration-landmarks.json',dict(coordinates='x4 within each 256x384 atlas cell',points=POINTS))
    for i,p in enumerate(poses):
        cx=(i%2)*256;cy=(i//2)*384;tx=p['x']*4-cx;ty=p['y']*4-cy
        orig=Image.open(ROOT/p['source']).convert('RGBA')
        nativebody,shadow=masks(p)
        # The walking floor dither shares palette entries with dark boot shading.
        # Preserve boot interiors; the correction polygons only classify source pixels.
        footpolys=[]
        if i==2:footpolys=[[(104,250),(116,256),(121,275),(113,278),(103,268)],[(138,295),(151,297),(163,316),(166,324),(154,326),(142,314)]]
        if i==3:footpolys=[[(62,298),(71,308),(59,322),(43,326),(33,319),(34,310),(48,309)],[(195,291),(206,293),(212,303),(204,314),(184,318),(180,312)]]
        if footpolys:
            protect=Image.new('L',(256,384));draw=ImageDraw.Draw(protect)
            for poly in footpolys:draw.polygon(poly,fill=255)
            protect=np.asarray(protect.crop((tx,ty,tx+p['width']*4,ty+p['height']*4)).resize(orig.size,Image.Resampling.NEAREST))>127
            restore=shadow&protect;nativebody|=restore;shadow&=~protect
        Image.fromarray((nativebody*255).astype('uint8')).save(dbg/(p['name']+'-body-native.png'))
        Image.fromarray((shadow*255).astype('uint8')).save(dbg/(p['name']+'-shadow-native.png'))
        # Nearest native coverage + sub-HD-pixel AA avoids Lanczos ringing dots.
        native_body_hd=Image.fromarray((nativebody*255).astype('uint8')).resize((p['width']*4,p['height']*4),Image.Resampling.NEAREST)
        targetalpha=native_body_hd.filter(ImageFilter.GaussianBlur(1.6))
        aa=np.asarray(targetalpha).copy();aa[aa<12]=0;aa[aa>243]=255;targetalpha=Image.fromarray(aa)
        target=np.zeros((384,256),dtype=float);target[ty:ty+targetalpha.height,tx:tx+targetalpha.width]=np.asarray(targetalpha)/255.
        src=material.crop((cx,cy,cx+256,cy+384));sa=np.asarray(src).astype(float);sm=source_mask(src,i)
        Image.fromarray((sm*255).astype('uint8')).save(dbg/(p['name']+'-flux-body.png'))
        targetpts=np.array([x[0] for x in POINTS[i]],float);sourcepts=np.array([x[1] for x in POINTS[i]],float)
        corners=np.array([[0,0],[255,0],[0,383],[255,383]],float)
        deform=LinearNDInterpolator(np.vstack([targetpts,corners]),np.vstack([sourcepts,corners]))
        yy,xx=np.mgrid[:384,:256];coords=deform(np.column_stack([xx.ravel(),yy.ravel()])).reshape((384,256,2))
        sy=np.clip(coords[:,:,1],0,383);sx=np.clip(coords[:,:,0],0,255)
        # Project only samples outside the source body back onto its colour interior.
        # This repairs small silhouette residuals without importing the grey background.
        inner=ndi.binary_erosion(sm,iterations=1)
        distance,indices=ndi.distance_transform_edt(~inner,return_indices=True)
        ix=np.rint(sx).astype(int);iy=np.rint(sy).astype(int)
        outside=~inner[iy,ix];needed=outside&(target>.5)
        projected_distance=distance[iy,ix]
        sx=np.where(outside,indices[1,iy,ix],sx);sy=np.where(outside,indices[0,iy,ix],sy)
        warped=np.stack([ndi.map_coordinates(sa[:,:,c],[sy,sx],order=1,mode='nearest') for c in range(3)],axis=2)
        soft=ndi.gaussian_filter(warped,sigma=(.38,.38,0));warped=.55*warped+.45*soft
        # Native light/shade masses modulate the detailed FLUX material gently.
        original4=orig.resize((p['width']*4,p['height']*4),Image.Resampling.LANCZOS)
        crop=warped[ty:ty+targetalpha.height,tx:tx+targetalpha.width]
        oa=np.asarray(original4).astype(float);bm=np.asarray(targetalpha)/255.
        lumin=oa[:,:,:3]@np.array([.2126,.7152,.0722]);mean=ndi.gaussian_filter(lumin*bm,3)/np.maximum(.001,ndi.gaussian_filter(bm,3))
        illum=np.clip((mean+20)/(np.median(mean[bm>.5])+20),.55,1.45)
        crop*=np.power(illum[:,:,None],.18)
        ungrained=np.clip(crop,0,255).astype('uint8')
        rng=np.random.default_rng(1711202612+i)
        noise=rng.normal(0,1.35,crop.shape[:2])[:,:,None]
        crop=np.clip(crop+noise,0,255).astype('uint8')
        # Original floor footprint, converted to neutral translucent shade.
        # Separate shadow alpha avoids reintroducing the original RGB dither colours.
        shadow_hd=Image.fromarray((shadow*255).astype('uint8')).resize(original4.size,Image.Resampling.NEAREST)
        shadow_aa=np.asarray(shadow_hd.filter(ImageFilter.GaussianBlur(1.25))).copy()
        native_support=np.asarray(shadow_hd)>0
        shadow_aa[~ndi.binary_dilation(native_support,iterations=2)]=0
        shadow_aa=(shadow_aa.astype(float)*.58).astype('uint8')
        floor=Image.new('RGBA',original4.size,(8,9,10,0));floor.putalpha(Image.fromarray(shadow_aa))
        body=Image.fromarray(crop,'RGB').convert('RGBA');body.putalpha(targetalpha)
        final=floor.copy();final.alpha_composite(body)
        beforegrain=Image.fromarray(ungrained,'RGB').convert('RGBA');beforegrain.putalpha(targetalpha)
        no_grain=floor.copy();no_grain.alpha_composite(beforegrain)
        final.save(dest/(p['name']+'-x4.png'))
        body.save(dest/(p['name']+'-body-x4.png'));floor.save(dest/(p['name']+'-shadow-x4.png'))
        final.resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-x2.png'))
        full.alpha_composite(final,(p['x']*4,p['y']*4));rawfull.alpha_composite(no_grain,(p['x']*4,p['y']*4))
        np.savez_compressed(dbg/(p['name']+'-mapping.npz'),source_x=sx,source_y=sy)
        native_nearest=np.asarray(native_body_hd)>127
        alpha_binary=np.asarray(targetalpha)>127
        jac=np.gradient(coords[:,:,0],axis=1)*np.gradient(coords[:,:,1],axis=0)-np.gradient(coords[:,:,0],axis=0)*np.gradient(coords[:,:,1],axis=1)
        metrics.append(dict(name=p['name'],native_body_silhouette_iou=float((native_nearest&alpha_binary).sum()/max(1,(native_nearest|alpha_binary).sum())),
            original_alpha_exact=False,alpha_policy='Native body contour with 1.6-HD-pixel antialiasing; source floor mask neutralized and softened 1.25px, opacity .58',source_lower_polygons=SOURCE_LOWER[i],
            inverse_warp_fold_fraction=float((jac[target>.5]<0).mean()),
            projected_body_fraction=float(needed.sum()/max(1,(target>.5).sum())),
            projection_distance_p95=float(np.percentile(projected_distance[needed],95)) if needed.any() else 0,
            original_native_shadow_pixels=int(shadow.sum()),foot_classification_polygons=footpolys,
            output_sha256=sha(dest/(p['name']+'-x4.png'))))
    full.save(dest/'atlas-x4.png');full.resize((256,384),Image.Resampling.LANCZOS).save(dest/'atlas-x2.png');rawfull.save(dest/'atlas-before-grain.png')
    save(OUT/'registration-qa.json',dict(method='Piecewise affine landmark retargeting + residual sampling projection; native alpha/shadows, restrained original light modulation',
        grain=dict(seed=1711202612,sigma_rgb=1.35,monochrome=True),softening=dict(gaussian_sigma_hd=.38,blend=.45),
        light_modulation_exponent=.18,frames=metrics,automatic_animation_validation=False))
    print(metrics,flush=True)
if __name__=='__main__':main()
