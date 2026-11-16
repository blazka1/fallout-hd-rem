"""Analyze generated atlas cells and retain exact native registration metadata."""
from pathlib import Path
import hashlib,json
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
refs=json.loads((RUN/'reference/manifest.json').read_text())['entries']
plans=[]
for d in range(6):
    path=RUN/f'raw/d{d}.png'; im=Image.open(path).convert('RGBA'); a=np.asarray(im)[:,:,3]
    for r in (r for r in refs if r['direction']==d):
        cell=r['cell'];x0=round((cell%3)*im.width/3);x1=round((cell%3+1)*im.width/3)
        y0=round((cell//3)*im.height/3);y1=round((cell//3+1)*im.height/3)
        yy,xx=np.where(a[y0:y1,x0:x1]>=32)
        assert len(xx)>1000, r['stem']
        crop=[int(x0+xx.min()),int(y0+yy.min()),int(xx.max()-xx.min()+1),int(yy.max()-yy.min()+1)]
        assert min(crop[0]-x0,crop[1]-y0,x1-crop[0]-crop[2],y1-crop[1]-crop[3])>=3,r['stem']
        target=r['target_bbox_x4']
        sx=(target[2]-target[0])/crop[2];sy=(target[3]-target[1])/crop[3]
        plans.append({**r,'atlas':str(path),'atlas_sha256':sha(path),'source_crop':crop,
            'target_rect':[target[0],target[1],target[2]-target[0],target[3]-target[1]],
            'anisotropy':max(sx,sy)/min(sx,sy),'alpha_threshold_for_crop':32})
(RUN/'registration-plan.json').write_text(json.dumps({'entries':plans,'method':'BBox registration to existing approved HD frame, native CE sizes unchanged; generated alpha retained'},indent=2),encoding='utf-8')
print(json.dumps({'frames':len(plans),'max_anisotropy':max(p['anisotropy'] for p in plans),'min_shadow_pixels':min(p['shadow_pixels'] for p in plans),'max_shadow_pixels':max(p['shadow_pixels'] for p in plans)}))
