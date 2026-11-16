"""Pixel QA and original/HD animation previews; no artistic processing."""
from pathlib import Path
import collections,hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2]
O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
inv=read(O/'inventory.json');prepared={p.stem:p for p in (O/'prepared-v2').rglob('u*.png')}
selection=read(O/'selection.json') if (O/'selection.json').exists() else {}
for key,path in selection.get('images',{}).items():prepared[key]=O/path
D=O/'review';D.mkdir(exist_ok=True)
groups=collections.defaultdict(list)
for r in inv['frames']:groups[(r['code'],r['direction'])].append(r)
qa=[]
for key,path in sorted(prepared.items()):
    im=Image.open(path).convert('RGBA');orig=Image.open(O/'source/frames'/f'{key}.png').convert('RGBA')
    expected=orig.resize((orig.width*4,orig.height*4),Image.Resampling.NEAREST)
    a=np.array(im);b=np.array(expected)
    qa.append(dict(id=key,size=list(im.size),dimensions_match=im.size==expected.size,
        exact_original_alpha=bool(np.array_equal(a[:,:,3],b[:,:,3])),
        changed_opaque_pixels=int(np.any(a[:,:,:3]!=b[:,:,:3],axis=2)[b[:,:,3]>0].sum()),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
report=dict(status='partial preview' if len(prepared)<inv['unique_frames'] else 'full asset QA',
    expected_unique=inv['unique_frames'],prepared_unique=len(prepared),checks=qa,
    passed=sum(int(x['dimensions_match'])+int(x['exact_original_alpha'])+int(x['changed_opaque_pixels']>0) for x in qa),
    failed=sum(int(not x['dimensions_match'])+int(not x['exact_original_alpha'])+int(x['changed_opaque_pixels']==0) for x in qa))
if 'u0373' in prepared:
    im=np.array(Image.open(prepared['u0373']).convert('RGBA'))
    original=Image.open(O/'source/frames/u0373.png').convert('RGBA').resize((680,900),Image.Resampling.NEAREST)
    mask=Image.open(O/selection.get('aimed_validation_mask','source/aimed-body-mask-native.png')).resize((680,900),Image.Resampling.NEAREST)
    protected=np.array(mask)==0
    matches=bool(np.array_equal(im[protected],np.array(original)[protected]))
    report['aimed_protected_pixels']=int(protected.sum());report['aimed_technical_lines_exact']=matches
    report['passed']+=int(matches);report['failed']+=int(not matches)
(D/'asset-qa.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
for code in sorted(set(k[0] for k in groups)):
    rs=[r for r in inv['frames'] if r['code']==code]
    if any(r['unique'] not in prepared for r in rs):continue
    if code=='na':
        r=rs[0];hd=Image.open(prepared[r['unique']]).convert('RGBA');old=Image.open(O/'source/frames'/f'{r["unique"]}.png').convert('RGBA').resize(hd.size,Image.Resampling.NEAREST)
        out=Image.new('RGB',(hd.width*2,hd.height+32),(18,22,19));draw=ImageDraw.Draw(out)
        draw.text((12,8),'Original x4',fill='white');draw.text((hd.width+12,8),'Qwen 2.1 + SeedVR2',fill='white')
        out.paste(old,(0,32),old);out.paste(hd,(hd.width,32),hd);out.save(D/'aimed-comparison.png');continue
    count=max(r['frame'] for r in rs)+1;frames=[];positions={}
    for r in rs:
        rows=groups[(code,r['direction'])];f=r['frame']
        cumulative=[sum(x['frame_shift'][a] for x in rows if 0<x['frame']<=f) for a in range(2)]
        if code=='ab':cumulative=[cumulative[a]-f*sum(x['frame_shift'][a] for x in rows)/len(rows) for a in range(2)]
        positions[(r['direction'],f)]=[
            -(r['width']//2)*4+round((r['direction_offset'][0]+cumulative[0])*4),
            -(r['height']-1)*4+round((r['direction_offset'][1]+cumulative[1])*4)]
    minx=min(positions[(r['direction'],r['frame'])][0] for r in rs)
    miny=min(positions[(r['direction'],r['frame'])][1] for r in rs)
    maxx=max(positions[(r['direction'],r['frame'])][0]+r['width']*4 for r in rs)
    maxy=max(positions[(r['direction'],r['frame'])][1]+r['height']*4 for r in rs)
    cw=max(340,maxx-minx+40);ch=max(180,maxy-miny+60)
    for f in range(count):
        out=Image.new('RGB',(cw*2,ch*6),(30,34,30));draw=ImageDraw.Draw(out)
        for d in range(6):
            rows=groups[(code,d)];r=next(x for x in rows if x['frame']==min(f,len(rows)-1))
            for col in range(2):
                im=Image.open(prepared[r['unique']] if col else O/'source/frames'/f'{r["unique"]}.png').convert('RGBA')
                if not col:im=im.resize((r['width']*4,r['height']*4),Image.Resampling.NEAREST)
                dx,dy=positions[(r['direction'],r['frame'])]
                x=col*cw+20-minx+dx;y=d*ch+40-miny+dy
                out.paste(im,(x,y),im)
                draw.text((col*cw+8,d*ch+6),f'{"Original x4" if col==0 else "Qwen 2.1 + SeedVR2"} / {code} d{d} f{f}',fill=(222,224,210))
        frames.append(out)
    frames[0].save(D/f'{code}-comparison.png')
    if len(frames)>1:frames[0].save(D/f'{code}-comparison.gif',save_all=True,append_images=frames[1:],duration=round(1000/rs[0]['fps']/10)*10,loop=0,disposal=2)
    if len(frames)>1:frames[0].save(D/f'{code}-comparison.webp',save_all=True,append_images=frames[1:],duration=round(1000/rs[0]['fps']),loop=0,lossless=True)
print(json.dumps({k:report[k] for k in ['status','prepared_unique','passed','failed']}),flush=True)

# A quick view can include a partial pilot sheet before every direction is ready.
for panel in read(O/'panels.json'):
    if not all(r['unique'] in prepared for r in panel['slots']):continue
    rows=math.ceil(len(panel['slots'])/3)
    cw=max(340,max(r['width']*4 for r in panel['slots'])+40);ch=max(180,max(r['height']*4 for r in panel['slots'])+45)
    out=Image.new('RGB',(cw*3,rows*ch),(30,34,30));draw=ImageDraw.Draw(out)
    for i,r in enumerate(panel['slots']):
        x=(i%3)*cw;y=(i//3)*ch
        im=Image.open(prepared[r['unique']]).convert('RGBA');out.paste(im,(x+(cw-im.width)//2,y+25+(ch-25-im.height)//2),im)
        draw.text((x+8,y+5),f'{r["code"]} d{r["direction"]} f{r["frame"]}',fill='white')
    out.save(D/(panel['id']+'-hd.png'))
