"""Review actual sprite exports, alpha corridor, fabric values and runtime preservation."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/qwen-nose-fabric-v4-20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    d=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):d.update(b)
    return d.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def matte(im):
    bg=Image.new('RGBA',im.size,(62,64,66,255));bg.alpha_composite(im);return bg.convert('RGB')
def compare(a,b,path,title_a='Предыдущий вариант',title_b='Нос и ткань: новый вариант',scale=1):
    a=matte(a);b=matte(b)
    if scale!=1:a=a.resize((a.width*scale,a.height*scale),Image.Resampling.LANCZOS);b=b.resize(a.size,Image.Resampling.LANCZOS)
    w,he=a.size;canvas=Image.new('RGB',(w*2+48,he+68),(23,25,28));d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    for i,(im,title) in enumerate([(a,title_a),(b,title_b)]):
        x=16+i*(w+16);d.text((x,10),title,font=font,fill=(235,235,225));canvas.paste(im,(x,48))
    canvas.save(path)

plan=read(OUT/'plan.json');old=Image.open(ROOT/plan['source']).convert('RGBA')
new=Image.open(OUT/'composite-v2/candidate-x6.png').convert('RGBA')
old4=Image.open(ROOT/'assets/generated/player-male-vault13/qwen-face-v3-20261116/composite-lossless/candidate-x4.png').convert('RGBA')
new4=Image.open(OUT/'composite-v2/candidate-x4.png').convert('RGBA')
assert old.size==new.size==(768,1152) and old4.size==new4.size==(512,768)
a,b=np.asarray(old),np.asarray(new)
roi=np.zeros(a.shape[:2],bool);roi[720:762,562:592]=True
alpha_difference=a[:,:,3]!=b[:,:,3]
assert not np.any(alpha_difference&~roi),'Alpha changed outside the authorized profile region'
aa=a[:,:,3]>=128;bb=b[:,:,3]>=128
growth=bb&~aa;loss=aa&~bb
growth_dist=ndimage.distance_transform_edt(~aa)[growth]
loss_dist=ndimage.distance_transform_edt(aa)[loss]
max_growth=float(growth_dist.max()) if growth_dist.size else 0.
max_loss=float(loss_dist.max()) if loss_dist.size else 0.
assert max_growth<=5 and max_loss<=5,'Profile escaped the intended 4px x6 discrete corridor'
cloth=np.asarray(Image.open(OUT/'composite-v2/cloth-mask-used.png').convert('RGB'))[:,:,0]
allowed=(cloth>0);allowed[716:776,562:620]=True
diff=np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
seed=np.asarray(Image.open(ROOT/'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116/control-v2/seed-reference.png').convert('RGBA'))
floor_zone=np.zeros(roi.shape,bool)
floor_zone[396:576,:384]=True;floor_zone[396:576,384:]=True
floor_zone[946:1152,:384]=True;floor_zone[946:1152,384:]=True
floor_core=(seed[:,:,2]<30)&(seed[:,:,3]>=128)&floor_zone
floor_core_unchanged=not np.any(diff[floor_core])
assert floor_core_unchanged,'Original dark ground-shadow region changed'
outside=int(np.count_nonzero(diff[~allowed]));outside_max=int(diff[~allowed].max())
assert outside_max<=1,'Unexpected edit outside cloth and face regions'
lum_a=a[:,:,:3]@np.array([.2126,.7152,.0722]);lum_b=b[:,:,:3]@np.array([.2126,.7152,.0722])
strong=cloth>=240
ratio=float(lum_b[strong].mean()/lum_a[strong].mean())
preview=OUT/'preview';preview.mkdir(exist_ok=True)
compare(old4,new4,preview/'four-poses-before-after.png')
compare(old.crop((532,676,660,804)),new.crop((532,676,660,804)),preview/'profile-before-after.png',scale=4)
compare(old.crop((92,158,268,406)),new.crop((92,158,268,406)),preview/'fabric-before-after.png',scale=3)
matte(new4).save(preview/'new-four-poses.png');matte(new).save(preview/'new-four-poses-x6.png')
for stage in ['qwen-fabric','qwen-profile']:
    matte(Image.open(OUT/stage/'raw.png').convert('RGBA')).save(preview/(stage+'-raw-neutral.png'))
baseline=read(OUT/'runtime-art-baseline.json')
changed=[p for p,v in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
assert not changed,changed
rows=[]
for y in range(728,751):
    ar=np.flatnonzero(aa[y,555:605]);br=np.flatnonzero(bb[y,555:605])
    if ar.size and br.size:rows.append({'y':y,'old_left_x':int(ar[0])+555,'new_left_x':int(br[0])+555})
result=dict(status='artistic study, not installed',source=plan['source'],
    stages={s:read(OUT/s/'result.json') for s in ['qwen-fabric','qwen-profile','mask-floor-protection','composite-v2']},
    alpha_changed_only_in_profile_region=True,alpha_changed_pixels=int(alpha_difference.sum()),
    nose_opaque_growth_pixels=int(growth.sum()),nose_opaque_loss_pixels=int(loss.sum()),
    max_boundary_growth_x6=max_growth,max_boundary_loss_x6=max_loss,
    max_boundary_growth_x4=max_growth/1.5,profile_left_edges_by_row=rows,
    blue_cloth_mean_luminance_ratio=round(ratio,4),blue_cloth_mean_darker_percent=round((1-ratio)*100,2),
    original_dark_ground_shadow_core_exactly_preserved=floor_core_unchanged,
    outside_authorized_masks_changed_pixels=outside,outside_authorized_masks_max_channel_difference=outside_max,
    unchanged_runtime_art_and_executable_files=len(baseline),runtime_modified=False,
    notes=['Pose positions and complete alpha outside the local nose region are preserved',
           'Final garment edit uses original blue-fabric selection; yellow insignia and skin are protected',
           'Profile preview enlarges the actual finished sprite; raw generated head is separate',
           'Full walk-cycle stability has not been tested; no runtime installation'],
    files={str(p.relative_to(OUT)):sha(p) for p in preview.iterdir() if p.is_file()})
save(OUT/'result.json',result)
print(json.dumps({k:result[k] for k in ['alpha_changed_pixels','nose_opaque_growth_pixels','nose_opaque_loss_pixels','max_boundary_growth_x4','blue_cloth_mean_darker_percent','original_dark_ground_shadow_core_exactly_preserved','outside_authorized_masks_max_channel_difference','unchanged_runtime_art_and_executable_files']}))
