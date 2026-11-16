"""Display the three pipeline stages on neutral grounds; raw artwork is unchanged."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/original-seed-qwen-4poses-20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def composite(image,color):
    bg=Image.new('RGBA',image.size,(*color,255));bg.alpha_composite(image);return bg.convert('RGB')
preview=OUT/'preview';preview.mkdir(exist_ok=True)
original=Image.open(OUT/'inputs/original-nearest-x4.png').convert('RGBA')
seed=Image.open(OUT/'seedvr2/seedvr2-x4.png').convert('RGBA')
qwen=Image.open(OUT/'qwen/raw.png').convert('RGBA')
assert original.size==seed.size==qwen.size==(512,768)
background=(62,64,66)
panels=[composite(im,background) for im in [original,seed,qwen]]
comparison=Image.new('RGB',(1600,836),(23,25,28));draw=ImageDraw.Draw(comparison)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
for i,(title,panel) in enumerate(zip(['Оригинал ×4 (без обработки)','SeedVR2 ×4','SeedVR2 → Qwen 2.1'],panels)):
    x=16+i*528;draw.text((x,10),title,font=font,fill=(235,235,225));comparison.paste(panel,(x,48))
comparison.save(preview/'original-seed-qwen-comparison.png')
panels[2].save(preview/'qwen-neutral-background.png')
composite(qwen,(230,230,225)).save(preview/'qwen-light-background.png')
composite(qwen,(18,20,23)).save(preview/'qwen-dark-background.png')
poses=[]
for i,entry in enumerate(read(OUT/'plan.json')['poses']):
    cell=((i%2)*256,(i//2)*384,(i%2+1)*256,(i//2+1)*384)
    path=preview/(entry['name']+'-qwen.png');qwen.crop(cell).save(path)
    a=np.array(seed.crop(cell))[:,:,3];b=np.array(qwen.crop(cell))[:,:,3]
    ma=a>=128;mb=b>=128
    poses.append(dict(name=entry['name'],file=path.name,sha256=sha(path),alpha_silhouette_iou_seed_vs_qwen=float((ma&mb).sum()/max(1,(ma|mb).sum()))))
seed_alpha=np.array(seed)[:,:,3];lanczos_alpha=np.array(Image.open(OUT/'seedvr2/lanczos-x4.png'))[:,:,3]
assert np.array_equal(seed_alpha,lanczos_alpha)
protected=read(OUT/'runtime-art-baseline.json')
changed=[p for p,v in protected.items() if sha(ROOT/p)!=v];assert not changed,changed
result=dict(status='four original sprites processed for comparison, not installed',
    source='Original Fallout FRM sprites hmjmpsaa / hmjmpsab; no ImageGen reference',
    stages={'seedvr2':read(OUT/'seedvr2/result.json'),'qwen':read(OUT/'qwen/result.json')},
    working_size=[512,768],qwen_steps=25,qwen_cfg=1,qwen_denoise=1,
    seed_alpha_matches_lanczos_original=True,poses=poses,
    unchanged_runtime_art_and_executable_files=len(protected),runtime_modified=False,
    preview_note='Only alpha compositing over a neutral background and labels; no retouch, palette correction or forced original mask. Qwen raw RGBA retained.',
    alpha_note='Qwen stores purple RGB in nearly transparent pixels. Neutral/light/dark previews use the actual alpha; raw RGB-only viewing can appear purple.',
    limits=['Qwen changes fine silhouettes and anatomy; generated alpha is not registered to FRM for installation',
        'Four isolated poses do not prove temporal consistency of a full walk cycle'],
    files={str(p.relative_to(OUT)):sha(p) for p in preview.iterdir() if p.is_file()})
write(OUT/'result.json',result)
print(json.dumps({'poses':4,'seed_seconds':result['stages']['seedvr2']['elapsed_seconds'],
    'qwen_seconds':result['stages']['qwen']['elapsed_seconds'],'seed_alpha_preserved':True,
    'pose_mask_iou':[round(p['alpha_silhouette_iou_seed_vs_qwen'],3) for p in poses],
    'runtime_files_unchanged':len(protected),'runtime_modified':False}))
