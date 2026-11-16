"""Non-generative montage at the verified CE 1080p world scale.

Only grey-matte extraction, uniform half-size display and translation are used.
No FRM mask, pose deformation, cleanup generation, relighting or body repainting.
"""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[2]
ASSET=ROOT/'assets/generated/player-male-vault13/flux2-local-only-v13-20261117'
OUT=ASSET/'cave-preview-20261117'
SOURCE=ASSET/'final/four-poses.png'
SCENE=ROOT/'build/hd-player-world-integration-20261116/verified-player/player-classic-cave-hd.png'
NAMES=['stand-front','stand-back','walk-southeast','walk-west']
LABELS=['Стойка спереди','Стойка сзади','Шаг · юго-восток','Шаг · запад']

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)

def matte(cell):
    c=np.asarray(cell).astype(float);h,w=c.shape[:2];yy,xx=np.mgrid[:h,:w];x=xx/w;y=yy/h
    terms=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],axis=2)
    chroma=c.max(2)-c.min(2);lum=c.mean(2)
    bg_samples=(lum>135)&(chroma<12)
    # Smooth grey field, fitted only to the neutral empty background of this cell.
    coef=np.linalg.lstsq(terms[bg_samples],c[bg_samples],rcond=None)[0]
    bg=terms@coef
    for _ in range(2):
        bg_samples&=np.max(np.abs(c-bg),axis=2)<6
        coef=np.linalg.lstsq(terms[bg_samples],c[bg_samples],rcond=None)[0];bg=terms@coef
    delta=np.max(np.abs(c-bg),axis=2);visible=delta>5
    sat=chroma/np.maximum(c.max(2),1)
    coloured=(sat>.08)&(chroma>4)&(delta>25)
    body=(coloured|((yy<260)&(delta>45)))&visible
    body=ndi.binary_fill_holes(ndi.binary_closing(body,iterations=1))&visible
    # Keep original pixel locations. Neutral lower-floor pixels are the existing
    # generated shadow; recover their opacity against the old grey backdrop.
    opaque=ndi.binary_erosion(body,iterations=1)
    near=ndi.binary_dilation(body,iterations=2)&visible
    _,indices=ndi.distance_transform_edt(~opaque,return_indices=True)
    local= c[indices[0],indices[1]]
    vec=local-bg
    edge_a=np.sum((c-bg)*vec,axis=2)/np.maximum(np.sum(vec*vec,axis=2),1)
    lower=np.max(np.maximum((bg-c)/np.maximum(bg,1),(c-bg)/np.maximum(255-bg,1)),axis=2)
    lower=np.clip(lower,0,1)
    alpha=lower.copy()
    alpha[near]=np.maximum(lower[near],np.clip(edge_a[near],0,1))
    alpha[opaque]=1
    alpha[~visible]=0
    # Feasible unmatting: recomposition over the fitted grey reproduces source.
    rgb=np.divide(c-bg*(1-alpha[:,:,None]),np.maximum(alpha[:,:,None],1e-6))
    rgb=np.clip(rgb,0,255);rgb[alpha==0]=0
    rgba=np.dstack([np.rint(rgb),np.rint(alpha*255)]).astype('uint8')
    back=rgba[:,:,:3].astype(float)*(rgba[:,:,3:4]/255.)+bg*(1-rgba[:,:,3:4]/255.)
    err=np.abs(back-c)
    bbox=Image.fromarray((visible*255).astype('uint8')).getbbox()
    return Image.fromarray(rgba,'RGBA'),dict(foreground_bbox=bbox,
        recomposition_mae_visible=float(err[visible].mean()),recomposition_max_visible=float(err[visible].max()),
        background_fit_mae=float(np.abs(bg[bg_samples]-c[bg_samples]).mean()),
        opaque_core_pixels=int(opaque.sum()),visible_source_pixels=int(visible.sum()),
        no_visible_pixel_discarded=bool(np.all(rgba[:,:,3][visible]>0)))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    original_hash=sha(SOURCE);scene_hash=sha(SCENE)
    src=Image.open(SOURCE).convert('RGB');scene=Image.open(SCENE).convert('RGB')
    assert src.size==(512,768) and scene.size==(1920,1080)
    assert original_hash==json.loads((ASSET/'qa.json').read_text(encoding='utf8'))['final_sha256']
    # Saved render is 1920x1080; CE logical world is 960x540. x4 artwork -> x2 display.
    factor=.5
    crop_box=(1040,370,1460,750);floor_anchor=(1240,606)
    background=scene.crop(crop_box);background.save(OUT/'cave-background-1to1.png')
    panel_w,panel_h=background.size
    board=Image.new('RGB',(panel_w*2,58+(panel_h+28)*2+26),(24,27,28));d=ImageDraw.Draw(board)
    d.text((16,10),'FLUX · на фоне нашей пещеры',font=font(25),fill=(226,216,186))
    d.text((16,39),'Игровой масштаб 1080p · статический монтаж · позы и силуэты сохранены',font=font(15),fill=(174,186,177))
    metrics=[];panels=[]
    for i,name in enumerate(NAMES):
        cell=src.crop(((i%2)*256,(i//2)*384,(i%2+1)*256,(i//2+1)*384))
        rgba,qa=matte(cell);rgba.save(OUT/(name+'-matte-x4.png'))
        # Pillow RGBA resize handles premultiplied interpolation. Same scale for x/y.
        sprite=rgba.resize((128,192),Image.Resampling.LANCZOS)
        sprite.save(OUT/(name+'-display-x2.png'))
        pane=background.convert('RGBA')
        xy=(floor_anchor[0]-crop_box[0]-64,floor_anchor[1]-crop_box[1]-168)
        pane.alpha_composite(sprite,xy);pane=pane.convert('RGB');panels.append(pane)
        pane.save(OUT/(name+'-cave-1to1.png'))
        col=i%2;row=i//2;bx=col*panel_w;by=58+row*(panel_h+28)
        d.text((bx+12,by+4),LABELS[i],font=font(17),fill=(226,216,186))
        board.paste(pane,(bx,by+28))
        metrics.append(dict(name=name,matting=qa,display_size=[128,192],uniform_scale=factor,translation=list(xy),
            output_sha256=sha(OUT/(name+'-cave-1to1.png'))))
    d.text((16,board.height-22),'Цвет персонажа без коррекции под освещение сцены. Это предпросмотр, не установка в игру.',font=font(13),fill=(165,179,170))
    board.save(OUT/'four-frames-game-scale.png')
    assert sha(SOURCE)==original_hash and sha(SCENE)==scene_hash
    assert all(m['matting']['no_visible_pixel_discarded'] for m in metrics)
    assert all(m['matting']['recomposition_mae_visible']<1 for m in metrics)
    save(OUT/'manifest.json',dict(status='static montage, no game installation',source=str(SOURCE.relative_to(ROOT)),source_sha256=original_hash,
        scene=str(SCENE.relative_to(ROOT)),scene_sha256=scene_hash,scene_size=scene.size,
        logical_world=[960,540],display=[1920,1080],world_scale=2,art_density=4,uniform_asset_scale=.5,
        scale_evidence=['work/hd-world-pilot/tools/prepare-runtime.ps1 logical_size [960,540]',
                        'work/hd-world-pilot/fallout1-ce-main/src/game/hd_player_test.cc capture/saveCrop'],
        background_crop=crop_box,source_unchanged=True,scene_unchanged=True,generation_calls=0,
        nonuniform_scaling=False,pose_warp=False,original_frm_mask=False,relighting=False,
        matting='Non-generative extraction of existing grey backdrop; existing shadow opacity recovered. No new silhouette or shadow geometry.',frames=metrics,
        limitations=['Static montage; no game lighting/occlusion simulation','RGB source has no supplied alpha; matte is estimated and checked by grey recomposition']))
    print(json.dumps(dict(frames=metrics,source_unchanged=True,scene_unchanged=True,generation_calls=0),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
