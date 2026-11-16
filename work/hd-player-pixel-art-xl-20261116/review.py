"""Compare actual LoRA inference with zero-weight controls at identical settings."""
from pipeline import ROOT,OUT,OLD,read,save,sha,core
import sys
from PIL import Image,ImageDraw,ImageFont
import numpy as np
PLAN=read(OUT/'plan.json');POSES=PLAN['poses']
PREVIEW=OUT/'preview';PREVIEW.mkdir(exist_ok=True)
original=Image.open(OUT/'inputs/original-lanczos-x4.png').convert('RGBA')
mask=original.getchannel('A');body=(np.array(original)[:,:,3]>127)&(np.array(original)[:,:,:3].max(axis=2)>25)
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def composite(im,bg):
    canvas=Image.new('RGBA',im.size,(*bg,255));canvas.alpha_composite(im);return canvas.convert('RGB')
def crop(im,p,pad=0):
    return im.crop((p['x']*4-pad,p['y']*4-pad,(p['x']+p['width'])*4+pad,(p['y']+p['height'])*4+pad))

images={};qa=[]
for branch in ['direct','seed']:
    baseline=np.array(Image.open(OUT/branch/'lora-00/raw.png').convert('RGB'))
    for strength in [0,35,65]:
        name=f'{branch}/lora-{strength:02}';d=OUT/name
        if not (d/'result.json').exists():continue
        raw=Image.open(d/'raw.png').convert('RGB');assert raw.size==(512,768)
        out=raw.convert('RGBA');out.putalpha(mask);images[name]=out
        dest=d/'rgba';dest.mkdir(exist_ok=True);out.save(dest/'atlas-x4.png')
        out.resize((256,384),Image.Resampling.LANCZOS).save(dest/'atlas-x2.png')
        for p in POSES:
            sprite=crop(out,p);assert sprite.size==(p['width']*4,p['height']*4)
            assert np.array_equal(np.array(sprite)[:,:,3],np.array(crop(original,p))[:,:,3])
            sprite.save(dest/(p['name']+'-x4.png'))
            sprite.resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-x2.png'))
        composite(out,(235,232,221)).save(dest/'light.png');composite(out,(17,19,21)).save(dest/'dark.png')
        delta=np.abs(np.array(raw).astype(float)-baseline.astype(float))
        graph=read(d/'prompt-api.json');history=read(d/'history.json');result=read(d/'result.json')
        assert history['status']['status_str']=='success'
        reused=(d/'reference-reused.json').exists()
        if reused:
            assert strength==0 and np.array_equal(np.array(raw),np.array(Image.open(OLD/'seed-dream/d22/raw.png')))
        else:
            assert graph['6']['inputs']['model']==['9',0] and graph['3']['inputs']['clip']==['9',1]
            assert graph['9']['inputs']['strength_model']==strength/100
        assert sha(d/'raw.png')==result['files'][0]['sha256']
        qa.append(dict(branch=branch,lora_strength=strength/100,raw_sha256=sha(d/'raw.png'),
            body_rgb_mean_absolute_difference_vs_no_lora=float(delta[body].mean()),
            body_pixels_changed_percent=float((delta.max(axis=2)[body]>0).mean()*100),
            exact_original_mask=True,dimensions_correct=True,prompt_id=result['prompt_id'],seconds=result['elapsed_seconds'],reused_existing_control=reused))

def board(rows,path,scale=4,bg=(64,64,60)):
    labelw=230;cellw=210 if scale==4 else 150;cellh=300 if scale==4 else 170;top=115
    out=Image.new('RGB',(labelw+cellw*4,top+cellh*len(rows)+40),(25,28,29));draw=ImageDraw.Draw(out)
    draw.text((20,14),'Vault 13 · DreamShaper XL v2 Turbo + Pixel Art XL',font=font(25),fill=(226,219,190))
    draw.text((20,50),f'Четыре исходные позы · масштаб ×{scale} · denoise 0,22 · одинаковый seed',font=font(17),fill=(169,177,175))
    for i,title in enumerate(['Стойка спереди','Стойка сзади','Шаг · ЮВ · кадр 2','Шаг · З · кадр 6']):
        draw.text((labelw+i*cellw+8,86),title,font=font(16),fill=(208,208,193))
    for r,(title,note,im) in enumerate(rows):
        y=top+r*cellh;draw.multiline_text((18,y+22),title,font=font(21),fill=(224,213,162),spacing=6)
        draw.multiline_text((18,y+111),note,font=font(15),fill=(163,174,173),spacing=6)
        for i,p in enumerate(POSES):
            tile=Image.new('RGBA',(cellw-8,cellh-8),(*bg,255));sprite=crop(im,p,8)
            if scale!=4:sprite=sprite.resize((sprite.width*scale//4,sprite.height*scale//4),Image.Resampling.LANCZOS)
            tile.alpha_composite(sprite,((tile.width-sprite.width)//2,tile.height-15-sprite.height))
            out.paste(tile.convert('RGB'),(labelw+i*cellw,y))
    draw.text((20,out.height-29),'Маски и размеры сохранены отдельно. Экспериментальные кадры; анимация и установка не проверялись.',font=font(14),fill=(160,171,169))
    out.save(path)

for branch,label in [('direct','Оригинал → DS'),('seed','Оригинал → Seed\n→ DS')]:
    if not all(f'{branch}/lora-{s:02}' in images for s in [0,35,65]):continue
    rows=[(label, 'Без LoRA' if s==0 else f'Pixel Art XL: {s/100:.2f}',images[f'{branch}/lora-{s:02}']) for s in [0,35,65]]
    board(rows,PREVIEW/f'{branch}-strengths-x4.png')
    board(rows,PREVIEW/f'{branch}-strengths-x2.png',2)

if len(images)<6:
    print('Partial comparison available for completed branches:',list(images),flush=True)
    sys.exit(0)

rows=[('Оригинал\n→ DreamShaper','Без LoRA',images['direct/lora-00']),
      ('Оригинал\n→ DreamShaper\n+ Pixel Art XL','LoRA 0,65',images['direct/lora-65']),
      ('Оригинал → Seed\n→ DreamShaper','Без LoRA',images['seed/lora-00']),
      ('Оригинал → Seed\n→ DreamShaper\n+ Pixel Art XL','LoRA 0,65',images['seed/lora-65'])]
board(rows,PREVIEW/'comparison-x4.png')
board(rows,PREVIEW/'comparison-x2.png',2)
board(rows,PREVIEW/'comparison-light.png',bg=(230,226,214))
board(rows,PREVIEW/'comparison-dark.png',bg=(16,18,21))

scene_path=ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116/prepare-v2/cave-style-reference.png'
scene=Image.open(scene_path).convert('RGBA');montage=Image.new('RGB',(1280,1076))
for i,(title,note,im) in enumerate(rows):
    pane=scene.copy()
    for p,(x,y) in zip(POSES,[(20,402),(97,425),(177,410),(263,434)]):
        spr=crop(im,p).resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS);pane.alpha_composite(spr,(x,y-spr.height))
    tile=Image.new('RGB',(640,538),(25,28,29));tile.paste(pane.convert('RGB'),(0,58));d=ImageDraw.Draw(tile)
    d.text((12,8),title.replace('\n',' ')+' · '+note,font=font(18),fill=(226,217,186))
    d.text((12,33),'Статический монтаж ×2, без освещения и перекрытий CE',font=font(14),fill=(163,173,170))
    montage.paste(tile,((i%2)*640,(i//2)*538))
montage.save(PREVIEW/'cave-montage.png')

before=read(OUT/'protected-before.json');changed=[p for p,h in before.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
for p in POSES:assert sha(ROOT/p['source'])==p['sha256']
save(OUT/'qa.json',dict(status='experiment, no chosen game asset',runs=qa,protected_files_checked=len(before),protected_files_changed=changed,
    preview_scene=dict(file=str(scene_path.relative_to(ROOT)),sha256=sha(scene_path),type='static montage, not CE capture'),
    limits=['Original-mask equality does not prove matching internal geometry','No full animation cycle or gameplay verification','LoRA effect measured at low denoise .22; not a universal model evaluation']))
save(OUT/'server-used.json',core.h.req('/system_stats'))
assert not changed,'Inspect concurrent changes before reporting protected files unchanged.'
print(json.dumps(dict(variants=6,poses_with_lora=16,protected_files=len(before),changed_files=changed,
    differences=[dict(branch=r['branch'],weight=r['lora_strength'],mae=round(r['body_rgb_mean_absolute_difference_vs_no_lora'],3)) for r in qa]),ensure_ascii=False))
