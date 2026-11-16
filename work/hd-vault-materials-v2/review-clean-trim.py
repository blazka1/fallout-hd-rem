"""Read-only QA and comparison previews; never alters the selected sprite."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'assets/generated/v13ent-vault/clean-trim-v3-20261114/complete'
old=Image.open(ROOT/'assets/hd/v13ent/vault-materials-v2/asset-016.png').convert('RGBA')
new=Image.open(SRC/'asset-016.png').convert('RGBA')
a=np.array(old);b=np.array(new);mask=np.array(Image.open(SRC/'edit-mask.png').convert('RGB'))[:,:,0]>0
assert np.array_equal(a[:,:,3],b[:,:,3]) and np.array_equal(a[~mask],b[~mask])
info=dict(alpha_exact=True,outside_selection_exact=True,changed_pixels=int(np.any(a!=b,axis=2).sum()),selection_pixels=int(mask.sum()),mean_before=a[mask,:3].mean(axis=0).tolist(),mean_after=b[mask,:3].mean(axis=0).tolist())
(SRC/'qa.json').write_text(json.dumps(info,indent=2));print(info)
canvas=Image.new('RGB',(1368,956),(45,45,45));d=ImageDraw.Draw(canvas)
for y,label,im in [(0,'Before',old),(478,'After',new)]:
 d.text((12,y+6),label,fill='white');small=im.resize((684,448),Image.Resampling.LANCZOS);canvas.paste(small,(0,y+25),small)
 # Larger left-side crop makes the localized metal tone easy to review.
 crop=im.crop((0,200,240,700)).resize((432,900),Image.Resampling.NEAREST)
 # Keep the comparison compact: use an unscaled detail next to the whole frame.
 detail=im.crop((0,250,240,700));canvas.paste(detail,(710,y+25),detail)
canvas.save(SRC/'comparison.png')
bg=Image.new('RGBA',new.size,(55,55,55,255));bg.alpha_composite(new);bg.convert('RGB').save(SRC/'preview.png')
