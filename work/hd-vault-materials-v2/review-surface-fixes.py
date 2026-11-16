"""Read-only registration audit and comparison crops."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'assets/generated/v13ent-vault/surface-fixes-v4-20261114/prepared-v2'
old=Image.open(ROOT/'assets/hd/v13ent/vault-clean-trim-v3/asset-016.png').convert('RGBA')
new=Image.open(SRC/'asset-016.png').convert('RGBA')
a=np.array(old);b=np.array(new);mask=np.array(Image.open(SRC/'edit-mask.png').convert('RGB'))[:,:,0]>0
assert a.shape==b.shape and np.array_equal(a[:,:,3],b[:,:,3]) and np.array_equal(a[~mask],b[~mask])
info=dict(alpha_exact=True,outside_selection_exact=True,changed_pixels=int(np.any(a!=b,axis=2).sum()),selection_pixels=int(mask.sum()))
(SRC/'qa.json').write_text(json.dumps(info,indent=2));print(info)
canvas=Image.new('RGB',(1000,760),(40,40,40));d=ImageDraw.Draw(canvas)
for x,label,im in [(0,'Before',old),(500,'After',new)]:
 d.text((x+10,8),label,fill='white')
 # Entire left corner: clean side panel above, rusty recess below.
 crop=im.crop((0,180,470,896));canvas.paste(crop,(x+10,30),crop)
canvas.save(SRC/'comparison.png')
canvas=Image.new('RGB',(800,490),(40,40,40));d=ImageDraw.Draw(canvas)
for x,label,im in [(0,'Before',old),(400,'After',new)]:
 d.text((x+10,8),label,fill='white');crop=im.crop((224,576,416,800)).resize((384,448),Image.Resampling.NEAREST);canvas.paste(crop,(x+8,30),crop)
canvas.save(SRC/'recess-comparison.png')
bg=Image.new('RGBA',new.size,(50,50,50,255));bg.alpha_composite(new);bg.convert('RGB').save(SRC/'preview.png')
