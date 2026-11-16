"""Review four actual x4 sketches and prove protected alpha/head/runtime invariants."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116'
PREV=ROOT/'assets/generated/player-male-vault13/qwen-nose-fabric-v4-20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def matte(im,color=(62,64,66)):
    bg=Image.new('RGBA',im.size,(*color,255));bg.alpha_composite(im);return bg.convert('RGB')
def comparison(a,b,path,scale=1):
    a=matte(a);b=matte(b)
    if scale!=1:a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST);b=b.resize(a.size,Image.Resampling.NEAREST)
    w,he=a.size;out=Image.new('RGB',(w*2+48,he+68),(23,25,28));d=ImageDraw.Draw(out)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    for i,(im,title) in enumerate([(a,'Основа: предыдущий вариант'),(b,'Пыль и пиксельная фактура')]):
        x=16+i*(w+16);d.text((x,10),title,font=font,fill=(235,235,225));out.paste(im,(x,48))
    out.save(path)

plan=read(OUT/'plan.json')
old=Image.open(PREV/'composite-v2/candidate-x4.png').convert('RGBA')
new=Image.open(OUT/'finish-v2/candidate-x4.png').convert('RGBA')
assert old.size==new.size==(512,768)
a,b=np.asarray(old),np.asarray(new)
assert np.array_equal(a[:,:,3],b[:,:,3]),'Original x4 alpha changed'
mask=np.asarray(Image.open(OUT/'finish-v2/edit-mask-x4.png').convert('RGB'))[:,:,0]
diff=np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
outside=int(np.count_nonzero(diff[mask==0]));outside_max=int(diff[mask==0].max())
assert outside_max<=1,'Pixels outside edit region unexpectedly changed'
head_checks=[]
for (x,y,w,he) in plan['protected_heads_x6']:
    left=int(np.ceil(x/1.5))+2;top=int(np.ceil(y/1.5))+2
    right=int((x+w)/1.5)-2;bottom=int((y+he)/1.5)-2
    exact=np.array_equal(a[top:bottom,left:right],b[top:bottom,left:right])
    assert exact,'Protected head changed'
    head_checks.append(dict(region=[left,top,right,bottom],exact=exact))
preview=OUT/'preview';preview.mkdir(exist_ok=True)
comparison(old,new,preview/'before-after.png')
comparison(old.crop((60,104,184,284)),new.crop((60,104,184,284)),preview/'texture-before-after.png',scale=3)
matte(new).save(preview/'new-four-poses.png')
matte(new,(23,25,28)).save(preview/'new-four-poses-dark.png')
matte(new,(210,208,202)).save(preview/'new-four-poses-light.png')
matte(Image.open(OUT/'qwen/raw.png').convert('RGBA')).save(preview/'qwen-raw-neutral.png')
labels=['1 · Стойка спереди','2 · Стойка сзади','3 · Шаг, юго-восток','4 · Шаг, запад']
sheet=matte(new);d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
poses=[]
for i,name in enumerate(plan['pose_order']):
    x=i%2*256;y=i//2*384
    d.text((x+14,y+16),labels[i],font=font,fill=(225,222,211))
    box=(x,y,x+256,y+384);path=preview/(name+'.png');new.crop(box).save(path)
    poses.append(dict(pose=name,file=str(path.relative_to(OUT)),sha256=sha(path)))
sheet.save(preview/'four-sketches.png')
baseline=read(OUT/'runtime-art-baseline.json')
changed=[p for p,v in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
assert not changed,changed
result=dict(status='four draft sketches, not installed',source=plan['source'],
    stages={s:read(OUT/s/'result.json') for s in ['prepare-v2','qwen','finish-v2']},
    alpha_exactly_preserved=True,protected_heads=head_checks,
    outside_edit_mask_changed_pixels=outside,outside_edit_mask_max_channel_difference=outside_max,
    pixel_processing='ComfyUI area 512x768 to256x384, nearest-exact back, 50% RGB blend inside body edit mask only',
    poses=poses,unchanged_runtime_art_and_executable_files=len(baseline),runtime_modified=False,
    limits=['Four isolated poses do not establish animation stability','Style reference is a saved actual cave capture, not a new in-game test',
            'Previous ground-shadow tint and existing contour fringe are retained'],
    files={str(p.relative_to(OUT)):sha(p) for p in preview.iterdir() if p.is_file()})
save(OUT/'result.json',result)
print(json.dumps({'poses':len(poses),'alpha_preserved':True,'heads_preserved':4,'outside_mask_max_difference':outside_max,
    'runtime_files_unchanged':len(baseline),'qwen_seconds':result['stages']['qwen']['elapsed_seconds']}))
