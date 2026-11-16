"""Lossless F1HD encoding and QA only; no image edits."""
from pathlib import Path
import hashlib,json,struct,shutil,importlib.util
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
OUT=ROOT/'assets/hd/player-male-vault13/lighting-v2-x4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((RUN/'registration-plan.json').read_text())['entries']
registry=['# Male Vault13 relighting v2; original native dimensions, x4 RGBA; pose shadow companions']
records=[]
for p in plan:
    image=OUT/(p['stem']+'.png');im=Image.open(image).convert('RGBA');rgba=im.tobytes()
    w,h=p['native_dimensions'];assert im.size==(w*4,h*4)
    a=np.asarray(im)[:,:,3];assert a.min()==0 and a.max()>=240
    payload=b'F1HD'+struct.pack('<4I',1,w*4,h*4,4)+rgba
    raw=OUT/(p['stem']+'.rgba');raw.write_bytes(payload)
    mask=RUN/'reference'/p['shadow_mask'];shadow=OUT/p['shadow_mask']
    assert len(mask.read_bytes())==w*h and set(mask.read_bytes())<={0,1} and p['shadow_pixels']>0
    shutil.copyfile(mask,shadow)
    registry.append(f"{p['animation']}\t{p['direction']}\t{p['frame']}\t{w}\t{h}\t{raw.name}")
    old=np.asarray(Image.open(p['hd_source']).convert('RGBA'));new=np.asarray(im)
    old_mask=old[:,:,3]>=128;new_mask=new[:,:,3]>=128
    intersection=(old_mask&new_mask).sum();union=(old_mask|new_mask).sum()
    records.append({**p,'filename':raw.name,'png':image.name,'png_sha256':sha(image),'rgba_sha256':sha(raw),
        'shadow_mask_sha256':sha(shadow),'silhouette_iou_previous_hd':float(intersection/max(1,union)),
        'solid_alpha_pixels':int(new_mask.sum()),'rgba_decoded_identical':payload[20:]==rgba})
(OUT/'registry.tsv').write_text('\n'.join(registry)+'\n',encoding='ascii')
(OUT/'manifest.json').write_text(json.dumps({'status':'prepared; runtime integration separate','image_count':54,
    'stand_directions':6,'walk_frames':48,'scale':4,'walk_fps':10,'format':'F1HD v1 RGBA8',
    'shadow_format':'native binary mask; runtime sigma0.85 blur and max145/255 floor-only blend',
    'registry_sha256':sha(OUT/'registry.tsv'),'entries':records},indent=2),encoding='utf-8')
# QA presentation only, preserving each registered image at native x4 size.
preview=RUN/'preview';preview.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
def contact(action,frame=0):
    canvas=Image.new('RGB',(960,680),(90,88,80));draw=ImageDraw.Draw(canvas)
    for d in range(6):
        stem=f'stand-d{d}' if action=='stand' else f'walk-d{d}-f{frame:03}'
        im=Image.open(OUT/(stem+'.png')).convert('RGBA')
        x=(d%3)*320+(320-im.width)//2;y=(d//3)*340+320-im.height
        canvas.paste(im,(x,y),im);draw.text(((d%3)*320+12,(d//3)*340+10),f'd{d} / {action} / f{frame}',font=font,fill='white')
    return canvas
contact('stand').save(preview/'stand-six-directions.png')
spec=importlib.util.spec_from_file_location('preview',ROOT/'work/hd-player-male/tools/create-runtime-preview.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
helper.animations([contact('walk',f) for f in range(8)],[100]*8,preview/'walk-six-directions-art')
print(json.dumps({'frames':len(records),'min_silhouette_iou':min(r['silhouette_iou_previous_hd'] for r in records),'average_silhouette_iou':sum(r['silhouette_iou_previous_hd'] for r in records)/54,'all_raw_roundtrips_identical':all(r['rgba_decoded_identical'] for r in records)}))
