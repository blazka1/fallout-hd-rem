"""Finalize cleaned FLUX colour with source-derived pose masks and floor shadows."""
from pipeline import ROOT,OUT,PREV,read,save,sha
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from scipy import ndimage as ndi
from scipy.interpolate import LinearNDInterpolator
import numpy as np

POINTS=[
 [([128,82],[130,80]),([121,94],[123,94]),([137,95],[141,94]),([135,111],[138,109]),([126,119],[130,117]),
  ([105,126],[104,127]),([155,120],[154,123]),([78,174],[80,174]),([80,202],[80,204]),([81,213],[81,215]),
  ([162,150],[163,151]),([164,175],[164,176]),([166,190],[166,191]),([125,203],[126,205]),
  ([108,247],[108,247]),([157,249],[157,249]),([89,310],[89,310]),([97,325],[98,325]),([170,304],[170,305])],
 [([128,84],[131,82]),([128,107],[131,105]),([126,119],[129,117]),([94,128],[97,128]),([149,135],[151,135]),
  ([80,165],[81,165]),([80,201],[81,201]),([82,213],[83,213]),([159,178],[160,178]),([162,225],[163,223]),
  ([126,209],[128,209]),([108,249],[109,249]),([154,250],[155,250]),([89,305],[90,306]),([85,312],[88,311]),([166,320],[170,322]),([177,323],[178,324])],
 [([128,76],[131,80]),([127,92],[130,94]),([133,109],[137,111]),([130,119],[132,119]),([104,122],[105,125]),([159,116],[157,121]),
  ([81,150],[83,151]),([80,181],[81,182]),([82,192],[82,194]),([171,150],[170,151]),([175,184],[174,185]),([174,202],[175,204]),
  ([133,210],[134,211]),([117,237],[116,237]),([129,245],[129,245]),([109,258],[110,258]),([112,272],[113,273]),
  ([139,283],[140,284]),([145,303],[146,303]),([154,319],[156,320]),([161,325],[162,325])],
 [([121,104],[123,106]),([108,113],[109,116]),([116,128],[119,131]),([128,136],[130,138]),([118,152],[121,153]),([150,150],[151,153]),
  ([106,183],[106,183]),([95,205],[96,206]),([162,185],[164,185]),([173,216],[174,216]),([175,230],[177,231]),
  ([129,222],[130,223]),([92,264],[92,264]),([66,305],[65,307]),([52,316],[51,319]),([42,314],[42,318]),
  ([171,264],[170,264]),([195,298],[196,298]),([199,310],[198,310]),([211,305],[209,306])]
]
LOWER=[
 [[(97,245),(120,248),(109,280),(99,299),(100,315),(111,328),(104,337),(88,334),(80,323),(84,296),(86,276)],
  [(145,244),(167,244),(171,279),(176,296),(185,307),(186,315),(173,321),(160,312),(154,288)]],
 [[(99,243),(120,246),(105,277),(99,298),(98,312),(91,320),(80,318),(81,304),(85,279)],
  [(143,243),(168,245),(169,279),(176,311),(188,320),(188,329),(174,335),(158,329),(155,311),(152,278)]],
 [[(106,237),(124,240),(119,258),(123,271),(120,281),(109,281),(99,269),(98,255)],
  [(124,240),(145,241),(146,276),(154,301),(169,317),(170,329),(155,331),(142,319),(134,289)]],
 [[(82,275),(102,280),(76,306),(63,323),(56,332),(41,333),(33,327),(31,318),(41,313),(55,310),(64,296)],
  [(165,271),(182,270),(197,289),(214,298),(220,306),(210,315),(199,320),(181,321),(178,313),(189,298)]]
]

def main():
    poses=read(OUT/'plan.json')['poses'];raw=Image.open(OUT/'registered-cleanup/raw.png').resize((512,768),Image.Resampling.LANCZOS)
    dest=OUT/'final';dest.mkdir(exist_ok=True);preview=OUT/'preview';preview.mkdir(exist_ok=True)
    atlas=Image.new('RGBA',(512,768));ungrained=Image.new('RGBA',(512,768));metrics=[]
    for i,p in enumerate(poses):
        cx=(i%2)*256;cy=(i//2)*384;tx=p['x']*4-cx;ty=p['y']*4-cy;w=p['width']*4;h=p['height']*4
        src=np.asarray(raw.crop((cx,cy,cx+256,cy+384))).astype(float)
        bg=np.median(np.concatenate([src[:16].reshape(-1,3),src[:,:16].reshape(-1,3)]),axis=0)
        sm=np.max(np.abs(src-bg),axis=2)>25
        allow=Image.new('L',(256,384));ad=ImageDraw.Draw(allow)
        ad.rectangle((0,0,255,260 if i<3 else 286),fill=255)
        for poly in LOWER[i]:ad.polygon(poly,fill=255)
        sm&=np.asarray(allow)>0
        sm=ndi.binary_closing(sm,iterations=1);sm=ndi.binary_fill_holes(sm)
        labels,n=ndi.label(sm);sizes=np.bincount(labels.ravel());sizes[0]=0;sm=labels==sizes.argmax()
        Image.fromarray((sm*255).astype('uint8')).save(OUT/'geometry'/(p['name']+'-cleanup-body.png'))
        tp=np.array([q[0] for q in POINTS[i]],float);sp=np.array([q[1] for q in POINTS[i]],float)
        corners=np.array([[0,0],[255,0],[0,383],[255,383]],float)
        f=LinearNDInterpolator(np.vstack([tp,corners]),np.vstack([sp,corners]))
        yy,xx=np.mgrid[ty:ty+h,tx:tx+w];xy=f(np.column_stack([xx.ravel(),yy.ravel()])).reshape(h,w,2)
        sx=np.clip(xy[:,:,0],0,255);sy=np.clip(xy[:,:,1],0,383);ix=np.rint(sx).astype(int);iy=np.rint(sy).astype(int)
        inner=ndi.binary_erosion(sm,iterations=1);dist,ind=ndi.distance_transform_edt(~inner,return_indices=True)
        bodyalpha=np.asarray(Image.open(OUT/'registered'/(p['name']+'-body-x4.png')).getchannel('A'))
        miss=~inner[iy,ix];needed=miss&(bodyalpha>127)
        dd=dist[iy,ix];sx=np.where(miss,ind[1,iy,ix],sx);sy=np.where(miss,ind[0,iy,ix],sy)
        colour=np.stack([ndi.map_coordinates(src[:,:,c],[sy,sx],order=1,mode='nearest') for c in range(3)],2)
        # Tone only the new saturated blue cloth toward the previous muted palette.
        blue=np.clip((colour[:,:,2]-colour[:,:,0]-3)/22,0,1)*np.clip((colour[:,:,2]-colour[:,:,1]+1)/12,0,1)
        luma=colour@np.array([.2126,.7152,.0722]);muted=(.73*colour+.27*luma[:,:,None])*.89
        colour=colour*(1-blue[:,:,None])+muted*blue[:,:,None]
        if i==1:
            # Reuse the larger clear FLUX-generated 13 from the prior local edit.
            # Replace its cloth neighbourhood too, so the tiny cleanup 13 disappears.
            old=np.asarray(Image.open(OUT/'registered'/(p['name']+'-body-x4.png')).convert('RGB')).astype(float)
            m=Image.new('L',(w,h));d=ImageDraw.Draw(m)
            d.polygon([(104-tx,122-ty),(146-tx,125-ty),(146-tx,168-ty),(105-tx,168-ty)],fill=255)
            m=np.asarray(m.filter(ImageFilter.GaussianBlur(3))).astype(float)/255
            colour=colour*(1-m[:,:,None])+old*m[:,:,None]
        colour=.65*colour+.35*ndi.gaussian_filter(colour,sigma=(.45,.45,0))
        before=np.clip(colour,0,255).astype('uint8')
        colour+=np.random.default_rng(1711202617+i).normal(0,.9,(h,w,1))
        body=Image.fromarray(np.clip(colour,0,255).astype('uint8'),'RGB').convert('RGBA');body.putalpha(Image.fromarray(bodyalpha))
        floor=Image.open(OUT/'registered'/(p['name']+'-shadow-x4.png')).convert('RGBA')
        final=floor.copy();final.alpha_composite(body)
        final.save(dest/(p['name']+'-x4.png'));final.resize((w//2,h//2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-x2.png'))
        body.save(dest/(p['name']+'-body-x4.png'));floor.save(dest/(p['name']+'-shadow-x4.png'))
        atlas.alpha_composite(final,(p['x']*4,p['y']*4))
        b=Image.fromarray(before,'RGB').convert('RGBA');b.putalpha(Image.fromarray(bodyalpha));n=floor.copy();n.alpha_composite(b);ungrained.alpha_composite(n,(p['x']*4,p['y']*4))
        metrics.append(dict(name=p['name'],size=[w,h],body_sample_projection_fraction=float(needed.sum()/max(1,(bodyalpha>127).sum())),
            body_sample_projection_p95=float(np.percentile(dd[needed],95)) if needed.any() else 0,
            sha256=sha(dest/(p['name']+'-x4.png'))))
    atlas.save(dest/'atlas-x4.png');atlas.resize((256,384),Image.Resampling.LANCZOS).save(dest/'atlas-x2.png');ungrained.save(dest/'atlas-before-grain.png')
    save(OUT/'finish-settings.json',dict(landmarks=POINTS,colour='Blue cloth only: 27% desaturation, 0.89 luminance scale, smoothly hue-masked',
        grain=dict(seed=1711202617,sigma=.9,monochrome=True),softening=dict(sigma=.45,blend=.35),
        back_13='Larger clear generated 13 and surrounding cloth reused from neckline-corrected registered FLUX; feather3',frames=metrics))
    make_previews(poses,atlas,preview)
    print(metrics,flush=True)

def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def cut(im,p,pad=4):return im.crop((p['x']*4-pad,p['y']*4-pad,(p['x']+p['width'])*4+pad,(p['y']+p['height'])*4+pad))
def make_previews(poses,atlas,out):
    orig=Image.open(OUT/'inputs/original-nearest-x4.png');prev=Image.open(PREV/'edit-v1/raw.png')
    def board(rows,path,scale=4,bg=(94,96,91)):
        labelw=190;cw=210 if scale==4 else 155;rh=290 if scale==4 else 166;top=105
        im=Image.new('RGB',(labelw+4*cw,top+len(rows)*rh+38),(25,28,29));d=ImageDraw.Draw(im)
        d.text((16,13),'Vault 13 · FLUX.2 klein 4B · доработка',font=font(25),fill=(230,219,188))
        d.text((16,49),'Горловина без отворотов · чистая грудь · читаемая 13 · позы и тени по оригиналу',font=font(16),fill=(177,185,173))
        for i,t in enumerate(['Стойка спереди','Стойка сзади','Шаг · юго-восток','Шаг · запад']):d.text((labelw+i*cw+8,80),t,font=font(15),fill=(210,213,197))
        for r,(label,note,src) in enumerate(rows):
            y=top+r*rh;d.multiline_text((16,y+25),label,font=font(21),fill=(228,211,158),spacing=5)
            d.multiline_text((16,y+101),note,font=font(14),fill=(169,180,169),spacing=5)
            for i,p in enumerate(poses):
                sp=cut(src,p).convert('RGBA')
                if scale!=4:sp=sp.resize((sp.width*scale//4,sp.height*scale//4),Image.Resampling.LANCZOS)
                tile=Image.new('RGBA',(cw-8,rh-8),(*bg,255));tile.alpha_composite(sp,((cw-8-sp.width)//2,rh-16-sp.height))
                im.paste(tile.convert('RGB'),(labelw+i*cw,y))
        d.text((16,im.height-26),'Четыре отдельных кадра для оценки · полный цикл и игровой рендер пока не проверялись',font=font(14),fill=(167,180,172));im.save(path)
    rows=[('Оригинал','Родные кадры\nNearest ×4',orig),('Первый FLUX','До исправлений\nСырой RGB',prev),('Доработанный','FLUX + подгонка\nТени отдельно',atlas)]
    board([rows[-1]],out/'four-poses.png');board(rows,out/'comparison-x4.png');board(rows,out/'comparison-x2.png',2)
    board([rows[-1]],out/'light.png',bg=(226,223,211));board([rows[-1]],out/'dark.png',bg=(21,23,26))
    # Static context only: no CE scene execution or lighting validation.
    scene=Image.open(ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116/prepare-v2/cave-style-reference.png').convert('RGBA')
    combined=Image.new('RGB',(1280,538),(25,28,29))
    for c,(label,src) in enumerate([('Оригинал',orig),('Доработанный FLUX',atlas)]):
        pane=scene.copy()
        for p,(x,y) in zip(poses,[(20,402),(97,425),(177,410),(263,434)]):
            sp=cut(src,p,0).resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS);pane.alpha_composite(sp,(x,y-sp.height))
        combined.paste(pane.convert('RGB'),(640*c,58));d=ImageDraw.Draw(combined)
        d.text((640*c+12,8),label,font=font(22),fill=(226,218,188));d.text((640*c+12,35),'Монтаж ×2 · не кадр игры, без освещения и перекрытий CE',font=font(14),fill=(166,181,172))
    combined.save(out/'cave-montage.png')

if __name__=='__main__':main()
