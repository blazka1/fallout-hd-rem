"""Compare the actual local edit, validate protected pixels, and preserve provenance."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/qwen-face-v3-20261116'
PREV=ROOT/'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    d=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):d.update(b)
    return d.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def matte(im):
    bg=Image.new('RGBA',im.size,(62,64,66,255));bg.alpha_composite(im);return bg.convert('RGB')

plan=read(OUT/'plan.json'); preview=OUT/'preview';preview.mkdir(exist_ok=True)
old6=Image.open(ROOT/plan['source']).convert('RGBA')
new6=Image.open(OUT/'composite-lossless/candidate-x6.png').convert('RGBA')
old4=Image.open(PREV/'qwen-soft/candidate-x4.png').convert('RGBA')
new4=Image.open(OUT/'composite-lossless/candidate-x4.png').convert('RGBA')
assert old6.size==new6.size==(768,1152)
assert old4.size==new4.size==(512,768)
mask=np.asarray(Image.open(OUT/'composite-lossless/edit-mask-x6.png').convert('RGB'))[:,:,0]>0
a,b=np.asarray(old6),np.asarray(new6)
diff=np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
alpha_equal=np.array_equal(a[:,:,3],b[:,:,3])
outside_count=int(np.count_nonzero(diff[~mask])); outside_max=int(diff[~mask].max())
regions=np.zeros(diff.shape,dtype=bool)
for f in plan['faces']:
    x,y,w,h=f['face'];regions[f['y']+y:f['y']+y+h,f['x']+x:f['x']+x+w]=True
outside_regions=int(np.count_nonzero(diff[~regions]))
assert alpha_equal,'Local face edit unexpectedly changed global alpha'
assert outside_max<=1,'Unexpected change outside the local face masks'
assert outside_regions==0,'Pixels outside authorized face rectangles changed'
assert np.array_equal(a[:576,384:],b[:576,384:]),'Rear-facing sprite changed'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
comparison=Image.new('RGB',(1072,836),(23,25,28));draw=ImageDraw.Draw(comparison)
for i,(im,title) in enumerate([(old4,'Предыдущий вариант'),(new4,'Новый проход: лицо')]):
    draw.text((16+i*528,10),title,font=font,fill=(235,235,225));comparison.paste(matte(im),(16+i*528,48))
comparison.save(preview/'four-poses-before-after.png')
face_sheet=Image.new('RGB',(1184,864),(23,25,28));draw=ImageDraw.Draw(face_sheet)
face_stats=[]
for row,(im,title) in enumerate([(old6,'До: предыдущий Qwen'),(new6,'После: новый проход по лицам')]):
    y=row*424;draw.text((16,y+8),title,font=font,fill=(235,235,225))
    for i,f in enumerate(plan['faces']):
        box=(f['x'],f['y'],f['x']+128,f['y']+128)
        # Enlargement for diagnostic viewing only. Exported sprites are not altered.
        crop=matte(im.crop(box)).resize((384,384),Image.Resampling.LANCZOS)
        face_sheet.paste(crop,(16+i*384,y+40))
        if row==1:
            x0,y0,w,h=f['face'];region=diff[f['y']+y0:f['y']+y0+h,f['x']+x0:f['x']+x0+w]
            face_stats.append(dict(pose=f['pose'],changed_pixels=int(np.count_nonzero(region)),mean_max_channel_change=round(float(region.mean()),3)))
face_sheet.save(preview/'faces-before-after.png')
matte(new4).save(preview/'new-four-poses.png')
matte(new6).save(preview/'new-four-poses-x6.png')
matte(Image.open(OUT/'qwen/heads-raw.png').convert('RGBA')).save(preview/'qwen-raw-heads-neutral.png')
baseline=read(OUT/'runtime-art-baseline.json')
changed=[p for p,v in baseline.items() if not (ROOT/p).exists() or sha(ROOT/p)!=v]
assert not changed,changed
result=dict(status='face study for visual review, not installed',source=plan['source'],
    qwen=read(OUT/'qwen/result.json'),composite=read(OUT/'composite-lossless/result.json'),
    alpha_exactly_preserved=alpha_equal,rear_view_exactly_preserved=True,
    outside_face_masks_changed_pixels=outside_count,outside_face_masks_max_channel_difference=outside_max,
    outside_face_rectangles_changed_pixels=outside_regions,
    mask_quantization_note='The saved 8-bit diagnostic mask rounds very low feather values to zero; 320 pixels there differ by at most one channel unit. Outside the three actual edit rectangles all RGBA pixels are identical.',
    faces=face_stats,unchanged_runtime_art_and_executable_files=len(baseline),runtime_modified=False,
    preview_note='Faces are shown enlarged 3x for inspection; the actual x6 sprite receives 44-46-pixel-wide local edits. Crops and compositing are ComfyUI nodes. Python only measures and lays out diagnostic previews.',
    limits=['This edit keeps the previous global alpha and floor shadows by design',
            'Previous blue cast-shadow tint and edge fringe have not been addressed',
            'Four poses are not a tested complete walk animation'],
    files={str(p.relative_to(OUT)):sha(p) for p in preview.iterdir() if p.is_file()})
save(OUT/'result.json',result)
print(json.dumps({k:result[k] for k in ['alpha_exactly_preserved','rear_view_exactly_preserved','outside_face_rectangles_changed_pixels','faces','unchanged_runtime_art_and_executable_files']},ensure_ascii=False))
