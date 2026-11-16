"""Registration mask only: preserve original targeted-shot callout lines."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
R=Path(__file__).resolve().parents[2]
O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
p=next(p for p in json.loads((O/'panels.json').read_text()) if p['id']=='na-p00');r=p['slots'][0]
source=Image.open(O/'source/frames/u0373.png').convert('RGBA');a=np.array(source)
green=(a[:,:,1]>32)&(a[:,:,1]>a[:,:,0]*1.5)&(a[:,:,1]>a[:,:,2]*1.5)
lines=np.zeros(green.shape,dtype=np.uint8)
for transposed in [False,True]:
    src=green.T if transposed else green;dst=lines.T if transposed else lines
    for y,row in enumerate(src):
        start=None
        for x in range(len(row)+1):
            value=x<len(row) and row[x]
            if value and start is None:start=x
            if not value and start is not None:
                if x-start>=8:dst[y,start:x]=255
                start=None
protected=Image.fromarray(lines).filter(ImageFilter.MaxFilter(3))
mask=Image.new('L',source.size);draw=ImageDraw.Draw(mask)
polygon=[(24,150),(29,136),(46,119),(58,111),(72,107),(78,87),(92,77),(106,76),(122,81),(133,91),
    (135,100),(148,98),(151,101),(144,105),(133,111),(130,123),(148,125),(152,129),(145,134),
    (136,137),(124,134),(116,130),(105,132),(97,141),(91,157),(88,157),(90,142),(78,133),
    (64,144),(45,153),(28,157),(24,154)]
draw.polygon(polygon,fill=255)
mask=Image.fromarray(np.where(np.array(protected)>0,0,np.array(mask)).astype(np.uint8))
panel=Image.new('RGB',tuple(p['size']))
panel.paste(mask.resize((r['width']*r['scale'],r['height']*r['scale']),Image.Resampling.NEAREST).convert('RGB'),(r['x'],r['y']))
panel.save(O/'source/aimed-body-mask-panel.png');mask.save(O/'source/aimed-body-mask-native.png');protected.save(O/'source/aimed-protected-lines.png')
info=dict(purpose='Geometric compositing mask, no generated artwork. Original straight technical callout lines and all pixels outside the body region remain exact original nearest x4 RGB.',
    polygon_native=polygon,protected_run_minimum=8,protected_margin_native=1,
    editable_native_pixels=int((np.array(mask)>0).sum()),source_sha256=hashlib.sha256((O/'source/frames/u0373.png').read_bytes()).hexdigest(),
    mask_sha256=hashlib.sha256((O/'source/aimed-body-mask-panel.png').read_bytes()).hexdigest())
(O/'source/aimed-mask.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8');print(json.dumps(info))
